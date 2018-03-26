import inspect

from flask import Flask
from flask_unchained import AppFactoryHook

from ..model_serializer import ModelSerializer


class RegisterSerializersHook(AppFactoryHook):
    bundle_module_name = 'serializers'
    name = 'serializers'
    priority = 15

    def process_objects(self, app: Flask, objects):
        for name, serializer in objects.items():
            model = serializer.Meta.model
            model_name = model if isinstance(model, str) else model.__name__
            self.store.serializers_by_model[model_name] = serializer

    def type_check(self, obj):
        if not inspect.isclass(obj):
            return False
        return issubclass(obj, ModelSerializer) and obj != ModelSerializer

    def update_shell_context(self, ctx: dict):
        ctx.update(self.store.serializers)
