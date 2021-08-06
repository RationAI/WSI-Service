import os
from importlib import reload

from fastapi.testclient import TestClient

from wsi_service.singletons import settings


def get_client_and_slide_manager():
    import wsi_service.api

    settings.local_mode = True
    settings.mapper_address = "http://testserver/slides/{slide_id}"
    settings.data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
    reload(wsi_service.api)
    return TestClient(wsi_service.api.api), wsi_service.api.slide_manager
