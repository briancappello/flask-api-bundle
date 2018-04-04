import inspect

from flask import Flask
from flask_unchained import AppFactoryHook

from ..model_serializer import ModelSerializer


class RegisterSerializersHook(AppFactoryHook):
    bundle_module_name = 'serializers'
    name = 'serializers'
    run_after = ['models']

    def process_objects(self, app: Flask, objects):
        for name, serializer in objects.items():
            self.store.serializers[name] = serializer

            model = serializer.Meta.model
            model_name = model if isinstance(model, str) else model.__name__
            kind = getattr(serializer, '__kind__', 'all')
            if kind == 'all':
                self.store.serializers_by_model[model_name] = serializer
            elif kind == 'create':
                self.store.create_by_model[model_name] = serializer
            elif kind == 'many':
                self.store.many_by_model[model_name] = serializer

    def type_check(self, obj):
        if not inspect.isclass(obj):
            return False
        return issubclass(obj, ModelSerializer) and obj != ModelSerializer

    def update_shell_context(self, ctx: dict):
        ctx.update(self.store.serializers)
