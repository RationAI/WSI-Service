from wsi_service.api.v3.singletons import localmapper
from wsi_service.api.v3.slides import add_routes_slides
from wsi_service.api.v3.local_mode import add_routes_local_mode


def add_routes_v3(app, settings, slide_manager):
    add_routes_slides(app, settings, slide_manager)
    if localmapper:
        slide_manager.with_local_mapper(local_mapper=localmapper)
        add_routes_local_mode(app, settings)
