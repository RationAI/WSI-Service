import io
import os
import shutil
from importlib import reload

import PIL.Image as Image
import pytest
from fastapi.testclient import TestClient

from wsi_service.__main__ import load_example_data


def setup_environment_variables():
    test_folder = os.path.dirname(os.path.realpath(__file__))
    os.environ["data_dir"] = os.path.join(test_folder, "data", "OpenSlide_adapted")
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
    load_example_data(os.path.join(os.environ["data_dir"]))
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


@pytest.fixture()
def client_changed_timeout():
    setup_environment_variables()
    if not os.path.exists(os.environ["data_dir"]):
        os.mkdir(os.environ["data_dir"])
    load_example_data(os.path.join(os.environ["data_dir"]))
    os.environ["inactive_histo_image_timeout_seconds"] = str(1)
    import wsi_service.api

    reload(wsi_service.api)
    yield TestClient(wsi_service.api.api), wsi_service.api.slide_source


def setup_mock(kwargs):
    mock = kwargs["requests_mock"]
    mock.get(
        "http://testserver/slides/f863c2ef155654b1af0387acc7ebdb60",
        json={
            "global_slide_id": "f863c2ef155654b1af0387acc7ebdb60",
            "global_case_id": "4593f30c39d75d2385c6c8811c4ae7e0",
            "local_slide_id": "CMU-1.svs",
            "storage_type": "fs",
            "storage_address": "Aperio/CMU-1.svs",
        },
    )
    mock.get(
        "http://testserver/slides/4b0ec5e0ec5e5e05ae9e500857314f20",
        json={
            "global_slide_id": "4b0ec5e0ec5e5e05ae9e500857314f20",
            "global_case_id": "491e1f7180445b1e805cdc128ba884b7",
            "local_slide_id": "CMU-1.tiff",
            "storage_type": "fs",
            "storage_address": "Generic TIFF/CMU-1.tiff",
        },
    )
    mock.get(
        "http://testserver/slides/7304006194f8530b9e19df1310a3670f",
        json={
            "global_slide_id": "7304006194f8530b9e19df1310a3670f",
            "global_case_id": "7636186ead725a9e9738dd4c623ece45",
            "local_slide_id": "Mirax2.2-1.mrxs",
            "storage_type": "fs",
            "storage_address": "MIRAX/Mirax2.2-1.mrxs",
        },
    )
    mock.get(
        "http://testserver/slides/c801ce3d1de45f2996e6a07b2d449bca",
        json={
            "global_slide_id": "c801ce3d1de45f2996e6a07b2d449bca",
            "global_case_id": "5b231a7f8cff5678958959bfae23b793",
            "local_slide_id": "OS-1.ndpi",
            "storage_type": "fs",
            "storage_address": "Hamamatsu/OS-1.ndpi",
        },
    )
    return mock


def get_image(response):
    return Image.open(io.BytesIO(response.raw.data))
