import io
import os

import PIL.Image as Image
import pytest
import tifffile

from wsi_service.__main__ import load_example_data


def setup_environment_variables():
    if "WS_DATA_PATH" in os.environ:
        os.environ["data_dir"] = os.environ["WS_DATA_PATH"]
    else:
        test_folder = os.path.dirname(os.path.realpath(__file__))
        os.environ["data_dir"] = os.path.join(test_folder, "data")
    os.environ["local_mode"] = str(True)
    os.environ["mapper_address"] = "http://testserver/slides/{slide_id}"
    os.environ["port_isyntax"] = "5556"


def make_dir_if_not_exists(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)


@pytest.fixture(scope="session")
def fetch_test_data():
    setup_environment_variables()
    make_dir_if_not_exists(os.environ["data_dir"])

    # load data and update update data_dir
    print(f"fetch data: " + os.environ["data_dir"])
    os.environ["data_dir"] = load_example_data(os.environ["data_dir"])


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
    mock.get(
        "http://testserver/slides/46061cfc30a65acab7a1ed644771a340",
        json={
            "slide_id": "46061cfc30a65acab7a1ed644771a340",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "Fluorescence OME-Tif/2019_10_15__0014_GOOD.ome.tif",
                    "main_address": True,
                    "storage_address_id": "46061cfc30a65acab7a1ed644771a340",
                    "slide_id": "46061cfc30a65acab7a1ed644771a340",
                }
            ],
        },
    )
    mock.get(
        "http://testserver/slides/56ed11a2a9e95f87a1e466cf720ceffa",
        json={
            "slide_id": "56ed11a2a9e95f87a1e466cf720ceffa",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "Fluorescence OME-Tif/LuCa-7color_Scan1.ome.tiff",
                    "main_address": True,
                    "storage_address_id": "56ed11a2a9e95f87a1e466cf720ceffa",
                    "slide_id": "56ed11a2a9e95f87a1e466cf720ceffa",
                }
            ],
        },
    )
    mock.get(
        "http://testserver/slides/cdad4692405c556ca63185bee512e95e",
        json={
            "slide_id": "cdad4692405c556ca63185bee512e95e",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "Ventana/OS-2.bif",
                    "main_address": True,
                    "storage_address_id": "cdad4692405c556ca63185bee512e95e",
                    "slide_id": "cdad4692405c556ca63185bee512e95e",
                }
            ],
        },
    )
    mock.get(
        "http://testserver/slides/c4682788c7e85d739ce043b3f6eaff70",
        json={
            "slide_id": "c4682788c7e85d739ce043b3f6eaff70",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "Leica/Leica-2.scn",
                    "main_address": True,
                    "storage_address_id": "c4682788c7e85d739ce043b3f6eaff70",
                    "slide_id": "c4682788c7e85d739ce043b3f6eaff70",
                }
            ],
        },
    )
    mock.get(
        "http://testserver/slides/5c1c0cc5cd3a501480fc6a4cb04ddda8",
        json={
            "slide_id": "5c1c0cc5cd3a501480fc6a4cb04ddda8",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "Philips iSyntax/4399.isyntax",
                    "main_address": True,
                    "storage_address_id": "5c1c0cc5cd3a501480fc6a4cb04ddda8",
                    "slide_id": "5c1c0cc5cd3a501480fc6a4cb04ddda8",
                }
            ],
        },
    )
    return mock
