import enum

from flask import Flask
from flask_unchained import Bundle

from .extensions import ma
from .model_resource import ModelResource


class FlaskApiBundle(Bundle):
    @classmethod
    def after_init_app(cls, app: Flask):
        from flask_sqlalchemy_bundle import BaseModel
        from flask_unchained import unchained
        from werkzeug.local import LocalProxy

        class JSONEncoder(app.json_encoder):
            def default(self, obj):
                if isinstance(obj, LocalProxy):
                    obj = obj._get_current_object()

                if isinstance(obj, enum.Enum):
                    return obj.name

                if isinstance(obj, BaseModel):
                    model_name = obj.__class__.__name__
                    serializer_cls = (unchained.flask_api_bundle
                                      .serializers_by_model.get(model_name))
                    if serializer_cls:
                        return serializer_cls().dump(obj).data

                # FIXME serializer-many
                if (obj and isinstance(obj, (list, tuple))
                        and isinstance(obj[0], BaseModel)):
                    model_name = obj[0].__class__.__name__
                    serializer_cls = (unchained.flask_api_bundle
                                      .serializers_by_model.get(model_name))
                    if serializer_cls:
                        return serializer_cls(many=True).dump(obj).data

                return super().default(obj)

        app.json_encoder = JSONEncoder
