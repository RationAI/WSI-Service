from wsi_service.api.v1.slides import add_routes_slides


def add_routes_v1(app, settings, slide_manager):
    add_routes_slides(app, settings, slide_manager)
