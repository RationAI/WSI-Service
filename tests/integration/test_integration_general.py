import os
import shutil
import tempfile
from zipfile import ZipFile

import pytest
import requests

from tests.integration.plugin_example_tests.helpers import get_image


def test_alive():
    response = requests.get("http://localhost:8080/alive")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_cases_valid():
    response = requests.get("http://localhost:8080/cases/")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) > 10
    assert len(cases[0].keys()) == 3
    case = list(filter(lambda case: case["local_id"] == "Olympus", cases))[0]
    assert case["id"] == "7a32e2c36ca756d9b7df0b627ace4c12"


def test_get_available_slides_valid():
    response = requests.get("http://localhost:8080/cases/4593f30c39d75d2385c6c8811c4ae7e0/slides/")
    assert response.status_code == 200
    slides = response.json()
    slide = list(
        filter(lambda slide: slide["slide_storage"]["storage_addresses"][0]["address"].endswith("CMU-1.svs"), slides)
    )[0]
    assert len(slides) == 1
    assert len(slides[0].keys()) == 3
    assert slide["id"] == "8d32dba05a4558218880f06caf30d3ac"
    assert slide["local_id"] == "CMU-1.svs"
    assert slide["slide_storage"]["slide_id"] == "8d32dba05a4558218880f06caf30d3ac"
    assert slide["slide_storage"]["storage_type"] == "fs"
    assert slide["slide_storage"]["storage_addresses"][0]["main_address"] is True
    assert slide["slide_storage"]["storage_addresses"][0]["storage_address_id"] == "8d32dba05a4558218880f06caf30d3ac"
    assert slide["slide_storage"]["storage_addresses"][0]["address"].endswith("Aperio/CMU-1.svs")
    assert slide["slide_storage"]["storage_addresses"][0]["slide_id"] == "8d32dba05a4558218880f06caf30d3ac"


def test_get_slide_valid():
    response = requests.get("http://localhost:8080/slides/f5f3a03b77fb5e0497b95eaff84e9a21")
    assert response.status_code == 200
    slide = response.json()
    assert len(slide.keys()) == 3
    assert slide["id"] == "f5f3a03b77fb5e0497b95eaff84e9a21"
    assert slide["local_id"] == "CMU-1.tiff"
    assert slide["slide_storage"]["slide_id"] == "f5f3a03b77fb5e0497b95eaff84e9a21"
    assert slide["slide_storage"]["storage_type"] == "fs"
    assert slide["slide_storage"]["storage_addresses"][0]["main_address"] is True
    assert slide["slide_storage"]["storage_addresses"][0]["storage_address_id"] == "f5f3a03b77fb5e0497b95eaff84e9a21"
    assert slide["slide_storage"]["storage_addresses"][0]["address"].endswith("Generic TIFF/CMU-1.tiff")
    assert slide["slide_storage"]["storage_addresses"][0]["slide_id"] == "f5f3a03b77fb5e0497b95eaff84e9a21"


def test_get_available_slides_invalid_case_id():
    response = requests.get("http://localhost:8080/cases/invalid_id/slides/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Case with case_id invalid_id does not exist"


def test_get_slide_invalid_slide_id():
    response = requests.get("http://localhost:8080/slides/invalid_id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Slide with slide_id invalid_id does not exist"


@pytest.mark.parametrize("api_version", ["v1", "v3"])
@pytest.mark.parametrize("slide_id", ["f5f3a03b77fb5e0497b95eaff84e9a21"])
@pytest.mark.parametrize("tile_x, tile_y, level, expected_response, size", [(0, 0, 9, 200, (128, 128))])  # ok
def test_get_slide_tile_padding_color(api_version, slide_id, tile_x, tile_y, level, expected_response, size):

    response = requests.get(
        (
            f"http://localhost:8080/{api_version}/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}"
            "?image_format=png&padding_color=%23AABBCC"
        ),
        stream=True,
    )
    assert response.status_code == expected_response
    assert response.headers["content-type"] == "image/png"

    image = get_image(response)
    x, y = image.size
    assert (x == size[0]) and (y == size[1])
    assert image.getpixel((size[0] - 1, size[1] - 1)) == (170, 187, 204)


@pytest.mark.parametrize("api_version", ["v1", "v3"])
@pytest.mark.parametrize("slide_id", ["f5f3a03b77fb5e0497b95eaff84e9a21"])
@pytest.mark.parametrize(
    "tile_x, level, expected_response",
    [
        (10, 1, 200),  # ok
        (10, 0, 200),  # ok
        (10, -1, 422),  # level -1 fails
        (10, 9, 200),  # level 10 ist coarsest level
        (10, 16, 422),  # level fails
    ],
)
def test_get_slide_tile_invalid(api_version, slide_id, tile_x, level, expected_response):

    response = requests.get(
        f"http://localhost:8080/{api_version}/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_x}"
    )
    assert response.status_code == expected_response


@pytest.mark.parametrize("api_version", ["v1", "v3"])
@pytest.mark.parametrize("region_size", [-1, 0, 1, 256, 512, 10000])
def test_get_region_maximum_extent(api_version, region_size):

    level = 5
    start_x = 13
    start_y = 23
    slide_id = "45707118e3b55f1b8e03e1f19feee916"
    response = requests.get(
        f"http://localhost:8080/{api_version}/slides/{slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{region_size}/{region_size}"
    )
    if region_size * region_size > 25000000:
        assert response.status_code == 422  # requested data too large
    elif region_size <= 0:
        assert response.status_code == 422
    else:
        assert response.status_code == 200


@pytest.mark.parametrize("api_version", ["v3"])
@pytest.mark.parametrize(
    "slide_id, file_count, file_size",
    [
        ("8d32dba05a4558218880f06caf30d3ac", 1, 177552579),  # SVS
        ("50f3010ed9a55f04b2e0d88cd19c6923", 5, 184520422),  # DICOM
        # ("45707118e3b55f1b8e03e1f19feee916", 26, 2915564670),  # MRXS
        # ("0f9083099777557b9c5c1083be953396", 10, 244418134),  # VSF
    ],
)
def test_download(api_version, slide_id, file_count, file_size):
    def download_file(url, download_folder):
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            filename = r.headers["content-disposition"].replace("attachment;filename=", "")
            file_path = os.path.join(download_folder, filename)
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1_000_000):
                    f.write(chunk)
        return file_path

    def get_file_count(path):
        file_count = 0
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    file_count += 1
                elif entry.is_dir():
                    file_count += get_file_count(entry.path)
        return file_count

    def get_dir_size(path):
        dir_size = 0
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    dir_size += entry.stat().st_size
                elif entry.is_dir():
                    dir_size += get_dir_size(entry.path)
        return dir_size

    # create temp dir
    tmp_dir = tempfile.mkdtemp()
    # download
    file_path = download_file(f"http://localhost:8080/{api_version}/slides/{slide_id}/download", tmp_dir)
    assert os.path.exists(file_path)
    assert slide_id in file_path
    # unzip
    zf = ZipFile(file_path)
    output_dir = os.path.join(tmp_dir, slide_id)
    zf.extractall(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    assert get_file_count(output_dir) == file_count
    assert get_dir_size(output_dir) == file_size
    # remove temp dir
    shutil.rmtree(tmp_dir)
