import io
import os
import shutil
from importlib import reload

import PIL.Image as Image
import pytest
import tifffile
from fastapi.testclient import TestClient

from wsi_service.tests.test_helper import (
    make_dir_if_not_exists,
    setup_environment_variables,
)


def get_client():
    import wsi_service.api

    reload(wsi_service.api)
    return TestClient(wsi_service.api.api)


@pytest.fixture()
def client_invalid_data_dir():
    setup_environment_variables()
    os.environ["data_dir"] = os.environ["data_dir"] + "/non_existing_dir"
    yield get_client()


@pytest.fixture()
def client_no_data():
    setup_environment_variables()
    data_dir = os.environ["data_dir"]
    del os.environ["data_dir"]
    os.environ["data_dir"] = os.path.join(data_dir, "empty")
    make_dir_if_not_exists(os.environ["data_dir"])
    yield get_client()
    shutil.rmtree(os.environ["data_dir"])


@pytest.fixture()
def client_changed_timeout():
    setup_environment_variables()
    os.environ["data_dir"] = os.environ["WS_DATA_PATH"]
    make_dir_if_not_exists(os.environ["data_dir"])
    os.environ["inactive_histo_image_timeout_seconds"] = str(1)
    import wsi_service.api

    reload(wsi_service.api)
    yield TestClient(wsi_service.api.api), wsi_service.api.slide_source
