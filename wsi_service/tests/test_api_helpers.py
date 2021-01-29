import io
import os
import shutil
from importlib import reload

import PIL.Image as Image
import pytest
import tifffile
from fastapi.testclient import TestClient

from wsi_service.__main__ import load_example_data


def setup_environment_variables():
    if os.path.exists("/data/OpenSlide_adapted"):
        os.environ["data_dir"] = "/data/OpenSlide_adapted"
    else:
        test_folder = os.path.dirname(os.path.realpath(__file__))
        os.environ["data_dir"] = os.path.join(test_folder, "data", "OpenSlide_adapted")
    os.environ["local_mode"] = str(True)
    os.environ["mapper_address"] = "http://testserver/slides/{slide_id}"


def get_client():
    import wsi_service.api

    reload(wsi_service.api)
    return TestClient(wsi_service.api.api)


@pytest.fixture()
def client_invalid_data_dir():
    setup_environment_variables()
    os.environ["data_dir"] = "/data/non_existing_dir"
    yield get_client()


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
            "slide_id": "f863c2ef155654b1af0387acc7ebdb60",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "Aperio/CMU-1.svs",
                    "main_address": True,
                    "storage_address_id": "f863c2ef155654b1af0387acc7ebdb60",
                    "slide_id": "f863c2ef155654b1af0387acc7ebdb60",
                }
            ],
        },
    )
    mock.get(
        "http://testserver/slides/4b0ec5e0ec5e5e05ae9e500857314f20",
        json={
            "slide_id": "4b0ec5e0ec5e5e05ae9e500857314f20",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "Generic TIFF/CMU-1.tiff",
                    "main_address": True,
                    "storage_address_id": "4b0ec5e0ec5e5e05ae9e500857314f20",
                    "slide_id": "4b0ec5e0ec5e5e05ae9e500857314f20",
                }
            ],
        },
    )
    mock.get(
        "http://testserver/slides/7304006194f8530b9e19df1310a3670f",
        json={
            "slide_id": "7304006194f8530b9e19df1310a3670f",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "MIRAX/Mirax2.2-1.mrxs",
                    "main_address": True,
                    "storage_address_id": "7304006194f8530b9e19df1310a3670f",
                    "slide_id": "7304006194f8530b9e19df1310a3670f",
                }
            ],
        },
    )
    mock.get(
        "http://testserver/slides/c801ce3d1de45f2996e6a07b2d449bca",
        json={
            "slide_id": "c801ce3d1de45f2996e6a07b2d449bca",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "Hamamatsu/OS-1.ndpi",
                    "main_address": True,
                    "storage_address_id": "c801ce3d1de45f2996e6a07b2d449bca",
                    "slide_id": "c801ce3d1de45f2996e6a07b2d449bca",
                }
            ],
        },
    )
    return mock


def get_image(response):
    return Image.open(io.BytesIO(response.raw.data))


def get_tiff_image(response):
    return tifffile.TiffFile(io.BytesIO(response.raw.data))


def tiff_pixels_equal(tiff_image, pixel_location, testpixel):
    narray = tiff_image.asarray()
    pixel = narray[pixel_location[0]][pixel_location[1]][pixel_location[2]]
    if pixel != testpixel[pixel_location[0]]:
        return False
    return True
