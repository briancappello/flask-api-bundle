class Store:
    def __init__(self):
        self.resources_by_model = {}

        # FIXME this won't work with custom list serializers
        self.serializers_by_model = {}

    @property
    def serializers(self):
        return {serializer_cls.__name__: serializer_cls
                for serializer_cls in self.serializers_by_model.values()}
