from functools import wraps, partial
from io import BytesIO

from flask import send_file, request
from PIL import Image
from werkzeug.exceptions import BadRequest
from werkzeug.routing import IntegerConverter


class SignedIntConverter(IntegerConverter):
        regex = r'-?\d+'

supported_image_formats = {  # intersection of supported PIL formats and existing image MIME-types
    'bmp': 'image/bmp',
    'gif': 'image/gif',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'tiff': 'image/tiff'}
alternative_spellings = {'jpg': 'jpeg', 'tif': 'tiff'}

def make_image_response(pil_image, image_format, image_quality, resize_x=None, resize_y=None):
    if image_format in alternative_spellings:
        image_format = alternative_spellings[image_format]
    
    if image_format in supported_image_formats:
        io = BytesIO()
        pil_image.save(io, format=image_format, quality=image_quality)
        io.seek(0)
        return send_file(io, mimetype=supported_image_formats[image_format])
    else:
        raise BadRequest()

def image_request(default_image_format, default_image_quality):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # read image format
            image_format = request.args.get('format', default_image_format)
            if image_format not in supported_image_formats and image_format not in alternative_spellings:
                raise BadRequest()
            
            # read image quality
            try:
                image_quality = int(request.args.get('quality', default_image_quality))
            except TypeError:
                raise BadRequest()
            
            return func(*args, **kwargs, image_format=image_format, image_quality=image_quality)
        return wrapper
    return decorator