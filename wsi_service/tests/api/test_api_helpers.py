import io
import os
import shutil
from importlib import reload

import PIL.Image as Image
import pytest
import tifffile
from fastapi.testclient import TestClient

from wsi_service.singletons import settings
from wsi_service.tests.test_helper import make_dir_if_not_exists


def initialize_settings():
    settings.local_mode = True
    settings.mapper_address = "http://testserver/slides/{slide_id}"


def get_client():
    import wsi_service.api

    reload(wsi_service.api)
    return TestClient(wsi_service.api.api)


@pytest.fixture()
def client_invalid_data_dir():
    initialize_settings()
    temp_dir = settings.data_dir
    settings.data_dir = os.path.join(settings.data_dir, "non_existing_dir")
    yield get_client()
    settings.data_dir = temp_dir


@pytest.fixture()
def client_no_data():
    initialize_settings()
    temp_dir = settings.data_dir
    settings.data_dir = os.path.join(settings.data_dir, "empty")
    make_dir_if_not_exists(settings.data_dir)
    yield get_client()
    shutil.rmtree(settings.data_dir)
    settings.data_dir = temp_dir


@pytest.fixture()
def client_changed_timeout():
    initialize_settings()
    make_dir_if_not_exists(settings.data_dir)
    settings.inactive_histo_image_timeout_seconds = 1
    import wsi_service.api

    reload(wsi_service.api)
    yield TestClient(wsi_service.api.api), wsi_service.api.slide_source
