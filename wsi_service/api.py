import sys

from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

import wsi_service.version
from flasgger import swag_from
from wsi_service.api_utils import image_request, make_image_response
from wsi_service.slide_source import SlideSource


_swagger_global_slide_id_param = {
    'name': 'global_slide_id',
    'description': 'global slide id',
    'in': 'path',
    'type': 'string',
    'required': 'true'
}

_swagger_image_format_param = lambda default : {
    'name': 'image_format',
    'description': 'image format of the thumbnail',
    'in': 'query',
    'type': 'string',
    'enum': [
        'jpg',
        'jpeg',
        'png',
        'tif',
        'tiff',
        'bmp',
        'gif'
    ],
    'default': default
}

_swagger_image_quality_param = lambda default : {
    'name': 'image_quality',
    'description': 'image quality (0-100) of the thumbnail (only considered for specific formats)',
    'in': 'query',
    'type': 'int',
    'min': 0,
    'max': 100,
    'default': default
}


def create_blueprint(name, config, swagger_tags):
    api = Blueprint(name, __name__)
    api.config = config
    api.slide_source = SlideSource(
        config['MAPPER_ADDRESS'],
        config['DATA_DIR'],
        config['INACTIVE_HISTO_IMAGE_TIMEOUT_SECONDS'])


    @swag_from({
        'tags': swagger_tags,
        'parameters': [
            _swagger_global_slide_id_param
        ],
        'responses': {
            '200': {
                'description': 'OK'
            },
            '404': {
                'description': 'Invalid global_slide_id'
            }
        }
    })
    @api.route('/slides/<global_slide_id>/info')
    def get_slide_info(global_slide_id):
        """
        Metadata for slide with given id
        """
        slide = api.slide_source.get_slide(global_slide_id)
        return jsonify(slide.get_info())


    @swag_from({
        'tags': swagger_tags,
        'parameters': [
            _swagger_global_slide_id_param,
            {
                'name': 'max_x',
                'description': 'maximum width of thumbnail',
                'in': 'path',
                'type': 'integer',
                'required': 'true'
            },
            {
                'name': 'max_y',
                'description': 'maximum height of thumbnail',
                'in': 'path',
                'type': 'integer',
                'required': 'true'
            },
            _swagger_image_format_param(default='jpeg'),
            _swagger_image_quality_param(default=90)
        ],
        'produces': [
            'image/*'
        ],
        'responses': {
            '200': {
                'description': 'OK',
                'schema': {
                    'type':'file'
                }
            },
            '404': {
                'description': 'Invalid global_slide_id'
            },
            '500': {
                'description': 'Malformed parameters'
            }
        }
    })
    @api.route('/slides/<global_slide_id>/thumbnail/max_size/<int:max_x>/<int:max_y>')
    @image_request('jpeg', 90)
    def get_slide_thumbnail(global_slide_id, max_x, max_y, image_format, image_quality):
        """
        Thumbnail of slide with given maximum size
        """
        slide = api.slide_source.get_slide(global_slide_id)
        thumbnail = slide.get_thumbnail(max_x, max_y)
        return make_image_response(thumbnail, image_format, image_quality)


    @swag_from({
        'tags': swagger_tags,
        'parameters': [
            _swagger_global_slide_id_param,
            _swagger_image_format_param(default='jpeg'),
            _swagger_image_quality_param(default=90)
        ],
        'produces': [
            'image/*'
        ],
        'responses': {
            '200': {
                'description': 'OK',
                'schema': {
                    'type':'file'
                }
            },
            '404': {
                'description': 'Invalid global_slide_id'
            }
        }
    })
    @api.route('/slides/<global_slide_id>/label')
    @image_request('jpeg', 90)
    def get_slide_label(global_slide_id, image_format, image_quality):
        """
        The label image of the slide
        """
        slide = api.slide_source.get_slide(global_slide_id)
        label = slide.get_label()
        return make_image_response(label, image_format, image_quality)


    @swag_from({
        'tags': swagger_tags,
        'parameters': [
            _swagger_global_slide_id_param,
            _swagger_image_format_param(default='jpeg'),
            _swagger_image_quality_param(default=90)
        ],
        'produces': [
            'image/*'
        ],
        'responses': {
            '200': {
                'description': 'OK',
                'schema': {
                    'type':'file'
                }
            },
            '404': {
                'description': 'Invalid global_slide_id'
            }
        }
    })
    @api.route('/slides/<global_slide_id>/macro')
    @image_request('jpeg', 90)
    def get_slide_macro(global_slide_id, image_format, image_quality):
        """
        The macro image of the slide
        """
        slide = api.slide_source.get_slide(global_slide_id)
        macro = slide.get_macro()
        return make_image_response(macro, image_format, image_quality)


    @swag_from({
        'tags': swagger_tags,
        'parameters': [
            _swagger_global_slide_id_param,
            {
                'name': 'level',
                'description': 'pyramid level of region',
                'in': 'path',
                'type': 'integer',
                'min': 0,
                'required': 'true'
            },
            {
                'name': 'start_x',
                'description': 'x component of start coordinate of requested region',
                'in': 'path',
                'type': 'integer',
                'required': 'true'
            },
            {
                'name': 'start_y',
                'description': 'y component of start coordinate of requested region',
                'in': 'path',
                'type': 'integer',
                'required': 'true'
            },
            {
                'name': 'size_x',
                'description': 'width of requested region',
                'in': 'path',
                'type': 'integer',
                'required': 'true'
            },
            {
                'name': 'size_y',
                'description': 'height of requested region',
                'in': 'path',
                'type': 'integer',
                'required': 'true'
            },
            _swagger_image_format_param(default='jpeg'),
            _swagger_image_quality_param(default=90)
        ],
        'produces': [
            'image/*'
        ],
        'responses': {
            '200': {
                'description': 'OK',
                'schema': {
                    'type':'file'
                }
            },
            '404': {
                'description': 'Invalid global_slide_id'
            },
            '413': {
                'description': 'Requested region is too large'
            },
            '500': {
                'description': 'Malformed parameters'
            }
        }
    })
    @api.route('/slides/<global_slide_id>/region/level/<int:level>/start/<signed_int:start_x>/<signed_int:start_y>/size/<int:size_x>/<int:size_y>')
    @image_request('jpeg', 90)
    def get_slide_region(global_slide_id, level, start_x, start_y, size_x, size_y, image_format, image_quality):
        """
        Get region of the slide. Level 0 is highest (original) resolution. Each level has half the
        resolution and half the extent of the previous level. Coordinates are given with respect
        to the requested level.
        """
        if size_x * size_y > api.config.get('MAX_RETURNED_REGION_SIZE',  float('Inf')):
            raise RequestEntityTooLarge('Requested region may not contain more than %d pixels' % api.config['MAX_RETURNED_REGION_SIZE'])
        slide = api.slide_source.get_slide(global_slide_id)
        img = slide.get_region(level, start_x, start_y, size_x, size_y)
        return make_image_response(img, image_format, image_quality)


    @swag_from({
        'tags': swagger_tags,
        'parameters': [
            _swagger_global_slide_id_param,
            {
                'name': 'level',
                'description': 'pyramid level of region',
                'in': 'path',
                'type': 'integer',
                'min': 0,
                'required': 'true'
            },
            {
                'name': 'tile_x',
                'description': 'request the tile_x-th tile in x dimension',
                'in': 'path',
                'type': 'integer',
                'required': 'true'
            },
            {
                'name': 'tile_y',
                'description': 'request the tile_y-th tile in y dimension',
                'in': 'path',
                'type': 'integer',
                'required': 'true'
            },
            _swagger_image_format_param(default='jpeg'),
            _swagger_image_quality_param(default=90)
        ],
        'produces': [
            'image/*'
        ],
        'responses': {
            '200': {
                'description': 'OK',
                'schema': {
                    'type':'file'
                }
            },
            '404': {
                'description': 'Invalid global_slide_id'
            },
            '500': {
                'description': 'Malformed parameters'
            }
        }
    })
    @api.route('/slides/<global_slide_id>/tile/level/<int:level>/tile/<signed_int:tile_x>/<signed_int:tile_y>')
    @image_request('jpeg', 90)
    def get_slide_tile(global_slide_id, level, tile_x, tile_y, image_format, image_quality):
        """
        Get tile of the slide. Extent of the tile is given in slide metadata. Level 0 is highest
        (original) resolution. Each level has half the resolution and half the extent of the
        previous level. Coordinates are given with respect to tiles, i.e. tile coordinate n is the
        n-th tile in the respective dimension.
        """
        slide = api.slide_source.get_slide(global_slide_id)
        img = slide.get_tile(level, tile_x, tile_y)
        return make_image_response(img, image_format, image_quality)


    return api
