from flask import Blueprint, current_app, jsonify, request

import wsi_service.version
from flasgger import swag_from
from wsi_service.api_utils import make_image_response, image_request
from wsi_service.slide_source import SlideSource

_swagger_slide_id_param = {
    'name': 'slide_id',
    'description': 'slide id',
    'in': 'path',
    'type': 'string',
    'required': 'true'
}
_swagger_case_id_param = {
    'name': 'case_id',
    'description': 'case id',
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
    api.slide_source = SlideSource(
        config['DATA_DIR'],
        config['INACTIVE_HISTO_IMAGE_TIMEOUT_SECONDS'])



    @api.route('/cases')
    @swag_from({
        'tags': swagger_tags,
        'responses': {
            '200': {
                'description': 'OK'
            }
        }
    })
    def get_case_list():
        """
        List all cases
        """
        case_list = api.slide_source.get_cases()
        return jsonify(case_list)



    @api.route('/cases/<case_id>/slides')
    @swag_from({
        'tags': swagger_tags,
        'parameters': [
            _swagger_case_id_param
        ],
        'responses': {
            '200': {
                'description': 'OK'
            },
            '404': {
                'description': 'Invalid case_id'
            }
        }
    })
    def get_Case_slide_list(case_id):
        """
        List all slides for given case id
        """
        slide_list = api.slide_source.get_slides(case_id)
        return jsonify(slide_list)



    @swag_from({
        'tags': swagger_tags,
        'parameters': [
            _swagger_slide_id_param
        ],
        'responses': {
            '200': {
                'description': 'OK'
            },
            '404': {
                'description': 'Invalid slide_id'
            }
        }
    })
    @api.route('/slides/<slide_id>/info')
    def get_slide_info(slide_id):
        """
        Metadata for slide with given id
        """
        slide = api.slide_source.get_slide(slide_id)
        return jsonify(slide.get_info())



    @swag_from({
        'tags': swagger_tags,
        'parameters': [
            _swagger_slide_id_param,
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
                'description': 'Invalid slide_id'
            },
            '500': {
                'description': 'Malformed parameters'
            }
        }
    })
    @api.route('/slides/<slide_id>/thumbnail/max_size/<int:max_x>/<int:max_y>')
    @image_request('jpeg', 90)
    def get_slide_thumbnail(slide_id, max_x, max_y, image_format, image_quality):
        """
        Thumbnail of slide with given maximum size
        """
        slide = api.slide_source.get_slide(slide_id)
        thumbnail = slide.get_thumbnail(max_x, max_y)
        return make_image_response(thumbnail, image_format, image_quality)



    @swag_from({
        'tags': swagger_tags,
        'parameters': [
            _swagger_slide_id_param,
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
                'description': 'Invalid slide_id'
            }
        }
    })
    @api.route('/slides/<slide_id>/label')
    @image_request('jpeg', 90)
    def get_slide_label(slide_id, image_format, image_quality):
        """
        The label image of the slide
        """
        slide = api.slide_source.get_slide(slide_id)
        label = slide.get_label()
        return make_image_response(label, image_format, image_quality)



    @swag_from({
        'tags': swagger_tags,
        'parameters': [
            _swagger_slide_id_param,
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
                'description': 'Invalid slide_id'
            },
            '500': {
                'description': 'Malformed parameters'
            }
        }
    })
    @api.route('/slides/<slide_id>/region/level/<int:level>/start/<signed_int:start_x>/<signed_int:start_y>/size/<int:size_x>/<int:size_y>')
    @image_request('jpeg', 90)
    def get_slide_region(slide_id, level, start_x, start_y, size_x, size_y, image_format, image_quality):
        """
        Get region of the slide. Level 0 is highest (original) resolution. Each level has half the
        resolution and half the extent of the previous level. Coordinates are given with respect
        to the requested level.
        """
        slide = api.slide_source.get_slide(slide_id)
        img = slide.get_region(level, start_x, start_y, size_x, size_y)
        return make_image_response(img, image_format, image_quality)



    @swag_from({
        'tags': swagger_tags,
        'parameters': [
            _swagger_slide_id_param,
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
                'description': 'Invalid slide_id'
            },
            '500': {
                'description': 'Malformed parameters'
            }
        }
    })
    @api.route('/slides/<slide_id>/tile/level/<int:level>/tile/<signed_int:tile_x>/<signed_int:tile_y>')
    def get_slide_tile(slide_id, level, tile_x, tile_y, image_format, image_quality):
        """
        Get tile of the slide. Extent of the tile is given in slide metadata. Level 0 is highest
        (original) resolution. Each level has half the resolution and half the extent of the
        previous level. Coordinates are given with respect to tiles, i.e. tile coordinate n is the
        n-th tile in the respective dimension.
        """
        slide = api.slide_source.get_slide(slide_id)
        img = slide.get_tile(level, tile_x, tile_y)
        return make_image_response(img, image_format, image_quality)


    return api
