import os
from importlib import reload

from fastapi.testclient import TestClient

from wsi_service.singletons import settings


def get_client_and_slide_manager():
    import wsi_service.app

    settings.local_mode = "wsi_service.simple_mapper:SimpleMapper"
    settings.mapper_address = "http://testserver/slides/{slide_id}"
    settings.data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
    settings.image_handle_cache_size = 2
    reload(wsi_service.app)
    return TestClient(wsi_service.app.app), wsi_service.app.slide_manager
