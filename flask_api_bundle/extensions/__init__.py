from .marshmallow import Marshmallow


ma = Marshmallow()

EXTENSIONS = {
    'ma': (ma, ['db']),
}
