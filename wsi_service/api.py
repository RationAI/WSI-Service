from flask import Blueprint, current_app, jsonify, request

import wsi_service.version
from wsi_service.api_utils import make_image_response
from wsi_service.slide_source import SlideSource


def create_blueprint(name, config):
    api = Blueprint(name, __name__)
    api.slide_source = SlideSource(
        config['DATA_DIR'],
        config['INACTIVE_HISTO_IMAGE_TIMEOUT_SECONDS'])


    @api.route('/')
    @api.route('/server_info')
    def get_server_info():
        return jsonify({
            'api_version': 'v1',
            'server_version': wsi_service.__version__,
            'vendor': 'Fraunhofer MEVIS',
            'root_url': request.base_url.split('server_info')[0]
        })

    @api.route('/cases')
    def get_case_list():
        case_list = api.slide_source.get_cases()
        return jsonify(case_list)

    @api.route('/cases/<case_id>/slides')
    def get_Case_slide_list(case_id):
        slide_list = api.slide_source.get_slides(case_id)
        return jsonify(slide_list)

    @api.route('/slides/<slide_id>/info')
    def get_slide_info(slide_id):
        slide = api.slide_source.get_slide(slide_id)
        return jsonify(slide.get_info())

    @api.route('/slides/<slide_id>/thumbnail/max_size/<int:max_x>/<int:max_y>')
    @api.route('/slides/<slide_id>/thumbnail/max_size/<int:max_x>/<int:max_y>/type/<image_type>')
    @api.route('/slides/<slide_id>/thumbnail/max_size/<int:max_x>/<int:max_y>/type/jpeg/quality/<int:quality>')
    def get_slide_thumbnail(slide_id, max_x, max_y, image_type='jpeg', quality=90):
        slide = api.slide_source.get_slide(slide_id)
        thumbnail = slide.get_thumbnail(max_x, max_y)
        return make_image_response(thumbnail, image_type, quality)

    @api.route('/slides/<slide_id>/label')
    @api.route('/slides/<slide_id>/label/type/<image_type>')
    @api.route('/slides/<slide_id>/label/type/jpg/quality/<int:quality>')
    @api.route('/slides/<slide_id>/label/type/jpeg/quality/<int:quality>')
    def get_slide_label(slide_id, image_type='jpeg', quality=90):
        slide = api.slide_source.get_slide(slide_id)
        label = slide.get_label()
        return make_image_response(label, image_type, quality)

    @api.route('/slides/<slide_id>/region/level/<int:level>/start/<signed_int:start_x>/<signed_int:start_y>/size/<int:size_x>/<int:size_y>')
    @api.route('/slides/<slide_id>/region/level/<int:level>/start/<signed_int:start_x>/<signed_int:start_y>/size/<int:size_x>/<int:size_y>/type/<image_type>')
    @api.route('/slides/<slide_id>/region/level/<int:level>/start/<signed_int:start_x>/<signed_int:start_y>/size/<int:size_x>/<int:size_y>/type/jpg/quality/<int:quality>')
    @api.route('/slides/<slide_id>/region/level/<int:level>/start/<signed_int:start_x>/<signed_int:start_y>/size/<int:size_x>/<int:size_y>/type/jpeg/quality/<int:quality>')
    def get_slide_region(slide_id, level, start_x, start_y, size_x, size_y, image_type='jpeg', quality=90):
        slide = api.slide_source.get_slide(slide_id)
        img = slide.get_region(level, start_x, start_y, size_x, size_y)
        return make_image_response(img, image_type, quality)

    @api.route('/slides/<slide_id>/tile/level/<int:level>/tile/<signed_int:tile_x>/<signed_int:tile_y>')
    @api.route('/slides/<slide_id>/tile/level/<int:level>/tile/<signed_int:tile_x>/<signed_int:tile_y>/type/<image_type>')
    @api.route('/slides/<slide_id>/tile/level/<int:level>/tile/<signed_int:tile_x>/<signed_int:tile_y>/type/jpg/quality/<int:quality>')
    @api.route('/slides/<slide_id>/tile/level/<int:level>/tile/<signed_int:tile_x>/<signed_int:tile_y>/type/jpeg/quality/<int:quality>')
    def get_slide_tile(slide_id, level, tile_x, tile_y, image_type='jpeg', quality=90):
        slide = api.slide_source.get_slide(slide_id)
        img = slide.get_tile(level, tile_x, tile_y)
        return make_image_response(img, image_type, quality)


    return api
