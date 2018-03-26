from flask_marshmallow import Marshmallow


ma = Marshmallow()  # FIXME subclass and add marshmallow fields as attributes


EXTENSIONS = {
    'ma': (ma, ['db']),
}
