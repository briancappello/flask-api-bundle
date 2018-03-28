from flask_controller_bundle.attr_constants import ABSTRACT_ATTR
from flask_controller_bundle.metaclasses import deep_getattr
from flask_marshmallow.sqla import SchemaOpts
from flask_unchained import unchained
from flask_unchained.string_utils import camel_case, title_case
from marshmallow.exceptions import ValidationError
from marshmallow.marshalling import Unmarshaller as BaseUnmarshaller
from marshmallow_sqlalchemy.convert import (
    ModelConverter as BaseModelConverter, _should_exclude_field)
from marshmallow_sqlalchemy.schema import ModelSchemaMeta

from .extensions import ma


READ_ONLY_FIELDS = {'slug', 'created_at', 'updated_at'}


class ModelConverter(BaseModelConverter):
    def fields_for_model(self, model, include_fk=False, fields=None,
                         exclude=None, base_fields=None, dict_cls=dict):
        """
        Overridden to correctly name hybrid_property fields, eg given::

            class User(db.Model):
                _password = db.Column('password', db.String)

                @db.hybrid_property
                def password(self):
                    return self._password

                @password.setter
                def password(self, password):
                    self._password = hash_password(password)

        In this case upstream marshmallow_sqlalchemy uses '_password' for the
        field name, but we use 'password', as would be expected because it's
        the attribute name used for the public interface of the Model. In order
        for this logic to work, the column name must be specified and it must be
        the same as the hybrid property name. Otherwise we just fallback to the
        upstream naming convention.
        """
        result = dict_cls()
        base_fields = base_fields or {}
        for prop in model.__mapper__.iterate_properties:
            if _should_exclude_field(prop, fields=fields, exclude=exclude):
                continue

            attr_name = prop.key
            if hasattr(prop, 'columns'):
                if not include_fk:
                    # Only skip a column if there is no overriden column
                    # which does not have a Foreign Key.
                    for column in prop.columns:
                        if not column.foreign_keys:
                            break
                    else:
                        continue

                col_name = prop.columns[0].name
                if attr_name != col_name and hasattr(model, col_name):
                    attr_name = col_name

            field = base_fields.get(attr_name) or self.property2field(prop)
            if field:
                result[attr_name] = field
        return result

    def property2field(self, prop, instance=True, field_class=None, **kwargs):
        field = super().property2field(prop, instance, field_class, **kwargs)
        # when a column is not nullable, mark the field as required
        if hasattr(prop, 'columns'):
            col = prop.columns[0]
            # we skip primary key columns because there's no way to tell here if
            # we're generating fields for a create or an update
            if not col.primary_key and not col.nullable:
                field.required = True
        return field


class ModelSerializerOpts(SchemaOpts):
    def __init__(self, meta, **kwargs):
        super().__init__(meta, **kwargs)
        self.model_converter = getattr(meta, 'model_converter', ModelConverter)


class ModelSerializerMeta(ModelSchemaMeta):
    def __new__(mcs, name, bases, clsdict):
        if '__init__' in clsdict:
            clsdict['__init__'] = unchained.inject()(clsdict['__init__'])

        if ABSTRACT_ATTR in clsdict:
            return super().__new__(mcs, name, bases, clsdict)

        meta = deep_getattr(clsdict, bases, 'Meta', None)
        model_missing = False
        try:
            if meta.model is None:
                model_missing = True
        except AttributeError:
            model_missing = True

        if model_missing:
            raise AttributeError(f'{name} is missing the class '
                                 f'Meta model attribute')
        elif isinstance(meta.model, str):
            meta.model = unchained.flask_sqlalchemy_bundle.models[meta.model]

        clsdict['Meta'] = meta
        return super().__new__(mcs, name, bases, clsdict)


class Unmarshaller(BaseUnmarshaller):
    def deserialize(self, data, fields_dict, many=False, partial=False,
                    dict_class=dict, index_errors=True, index=None):
        # when data is None, which happens when a POST request was made with an
        # empty body, convert it to an empty dict. works around an exception
        # deep in marshmallow.schema.BaseSchema._invoke_field_validators where
        # it expects data to be a dict
        data = data or {}
        return super().deserialize(data, fields_dict, many, partial,
                                   dict_class, index_errors, index)
    __call__ = deserialize


class ModelSerializer(ma.ModelSchema, metaclass=ModelSerializerMeta):
    """
    Base class for database model serializers. This is pretty much a stock
    :class:`flask_marshmallow.sqla.ModelSchema`: it will automatically create
    fields from the attached database Model, the only difference being that it
    will automatically dump to (and load from) the camel-cased variants of the
    field names.

    For example::

        from backend.api import ModelSerializer
        from backend.security.models import Role

        class RoleSerializer(ModelSerializer):
            class Meta:
                model = Role

    Is roughly equivalent to::

        from marshmallow import Schema, fields

        class RoleSerializer(Schema):
            id = fields.Integer()
            name = fields.String()
            description = fields.String()
            created_at = fields.DateTime(dump_to='createdAt',
                                         load_from='createdAt')
            updated_at = fields.DateTime(dump_to='updatedAt',
                                         load_from='updatedAt')

    Obviously you probably shouldn't be loading `created_at` or `updated_at`
    from JSON; it's just an example to show the automatic snake-to-camelcase
    field naming conversion.
    """
    __abstract__ = True

    OPTIONS_CLASS = ModelSerializerOpts

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._unmarshal = Unmarshaller()

    def is_create(self):
        """
        Check if we're creating a new object. Note that this context flag
        must be set from the outside, ie when the class gets instantiated.
        """
        return self.context.get('is_create', False)

    def handle_error(self, error, data):
        """
        Customize the error messages for required/not-null validators with
        dynamically generated field names. This is definitely a little hacky
        (it mutates state, uses hardcoded strings), but unsure how better to do it
        """
        required_messages = {'Missing data for required field.',
                             'Field may not be null.'}
        for field_name in error.field_names:
            for i, msg in enumerate(error.messages[field_name]):
                if msg in required_messages:
                    label = title_case(field_name)
                    error.messages[field_name][i] = f'{label} is required.'

    def _update_fields(self, obj=None, many=False):
        """
        Overridden to automatically convert snake-cased field names to
        camel-cased (when dumping) and to load camel-cased field names back
        to their snake-cased counterparts
        """
        fields = super()._update_fields(obj, many)
        new_fields = self.dict_class()
        for name, field in fields.items():
            if (field.dump_to is None
                    and not name.startswith('_')
                    and '_' in name):
                camel_cased_name = camel_case(name)
                field.dump_to = camel_cased_name
                field.load_from = camel_cased_name
            if name in READ_ONLY_FIELDS:
                field.dump_only = True
            new_fields[name] = field

        # validate id
        if 'id' in new_fields:
            new_fields['id'].validators = [self.validate_id]

        self.fields = new_fields
        return new_fields

    def validate_id(self, id):
        if self.is_create() or int(id) == int(self.instance.id):
            return
        raise ValidationError('ids do not match')
