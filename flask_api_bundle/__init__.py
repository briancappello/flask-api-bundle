import enum

from flask import Flask
from flask_sqlalchemy_bundle import BaseModel
from flask_unchained import Bundle, unchained
from marshmallow import (fields, pre_load, post_load, pre_dump, post_dump,
                         validates, validates_schema, ValidationError)

from .model_resource import ModelResource
from .model_serializer import ModelSerializer


class FlaskApiBundle(Bundle):
    @classmethod
    def after_init_app(cls, app: Flask):
        class JSONEncoder(app.json_encoder):
            def default(self, obj):
                if isinstance(obj, enum.Enum):
                    return obj.name

                if isinstance(obj, BaseModel):
                    model_name = obj.__class__.__name__
                    serializer = (unchained
                                  .flask_api_bundle
                                  .serializers_by_model.get(model_name))
                    if serializer:
                        return serializer().dump(obj).data

                # FIXME serializer-many
                if (isinstance(obj, (list, tuple)) and obj
                        and isinstance(obj[0], BaseModel)):
                    model_name = obj[0].__class__.__name__
                    serializer = (unchained
                                  .flask_api_bundle
                                  .serializers_by_model.get(model_name))
                    if serializer:
                        return serializer(many=True).dump(obj).data

                return super().default(obj)

        app.json_encoder = JSONEncoder
