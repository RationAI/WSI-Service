import os
import shutil
from importlib import reload

import pytest
from fastapi.testclient import TestClient

from wsi_service.__main__ import load_example_data


def setup_environment_variables():
    test_folder = os.path.dirname(os.path.realpath(__file__))
    os.environ["data_dir"] = os.path.join(test_folder, "data/")
    os.environ["local_mode"] = str(True)
    os.environ["mapper_address"] = "http://testserver/slides/{global_slide_id}"


def get_client():
    import wsi_service.api

    reload(wsi_service.api)
    return TestClient(wsi_service.api.api)


@pytest.fixture()
def client():
    setup_environment_variables()
    if not os.path.exists(os.environ["data_dir"]):
        os.mkdir(os.environ["data_dir"])
    load_example_data(os.path.join(os.environ["data_dir"], "example"))
    yield get_client()


@pytest.fixture()
def client_no_data():
    setup_environment_variables()
    data_dir = os.environ["data_dir"]
    del os.environ["data_dir"]
    os.environ["data_dir"] = os.path.join(data_dir, "empty")
    if not os.path.exists(os.environ["data_dir"]):
        os.mkdir(os.environ["data_dir"])
    yield get_client()
    shutil.rmtree(os.environ["data_dir"])
