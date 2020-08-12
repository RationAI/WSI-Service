from io import BytesIO

from flask import send_file
from werkzeug.routing import IntegerConverter
from PIL import Image
from werkzeug.exceptions import BadRequest

class SignedIntConverter(IntegerConverter):
        regex = r'-?\d+'

supported_image_types = {  # intersection of supported PIL formats and existing image MIME-types
    'bmp': 'image/bmp',
    'gif': 'image/gif',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'tiff': 'image/tiff'}
alternative_spellings = {'jpg': 'jpeg', 'tif': 'tiff'}

def make_image_response(pil_image, image_type='jpeg', quality=90, resize_x=None, resize_y=None):
    if image_type in alternative_spellings:
        image_type = alternative_spellings[image_type]
    
    if image_type in supported_image_types:
        io = BytesIO()
        pil_image.save(io, format=image_type, quality=quality)
        io.seek(0)
        return send_file(io, mimetype=supported_image_types[image_type])
    else:
        raise BadRequest()
