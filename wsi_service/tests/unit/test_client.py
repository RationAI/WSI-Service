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


def setup_storage_mapper_mock(kwargs):
    mock = kwargs["requests_mock"]
    mock.get(
        "http://testserver/slides/fc1ef3789eac548883e9923455608e13",
        json={
            "slide_id": "fc1ef3789eac548883e9923455608e13",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "testcase/CMU-1-small.tiff",
                    "main_address": True,
                    "storage_address_id": "f863c2ef155654b1af0387acc7ebdb60",
                    "slide_id": "fc1ef3789eac548883e9923455608e13",
                }
            ],
        },
    )
    return mock
