import pytest
import requests

from wsi_service.tests.integration.plugin_example_tests.helpers import get_image


def test_alive():
    response = requests.get("http://localhost:8080/alive")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_cases_valid():
    response = requests.get("http://localhost:8080/v1/cases/")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) > 10
    assert len(cases[0].keys()) == 3
    case = list(filter(lambda case: case["local_id"] == "Olympus", cases))[0]
    assert case["id"] == "7a32e2c36ca756d9b7df0b627ace4c12"


def test_get_available_slides_valid():
    response = requests.get("http://localhost:8080/v1/cases/4593f30c39d75d2385c6c8811c4ae7e0/slides/")
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
    response = requests.get("http://localhost:8080/v1/slides/f5f3a03b77fb5e0497b95eaff84e9a21")
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
    response = requests.get("http://localhost:8080/v1/cases/invalid_id/slides/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Case with case_id invalid_id does not exist"


def test_get_slide_invalid_slide_id():
    response = requests.get("http://localhost:8080/v1/slides/invalid_id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Slide with slide_id invalid_id does not exist"


@pytest.mark.parametrize("slide_id", ["f5f3a03b77fb5e0497b95eaff84e9a21"])
@pytest.mark.parametrize("tile_x, tile_y, level, expected_response, size", [(0, 0, 9, 200, (128, 128))])  # ok
def test_get_slide_tile_padding_color(slide_id, tile_x, tile_y, level, expected_response, size):

    response = requests.get(
        f"http://localhost:8080/v1/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}?image_format=png&padding_color=%23AABBCC",
        stream=True,
    )
    assert response.status_code == expected_response
    assert response.headers["content-type"] == "image/png"

    image = get_image(response)
    x, y = image.size
    assert (x == size[0]) and (y == size[1])
    assert image.getpixel((size[0] - 1, size[1] - 1)) == (170, 187, 204)


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
def test_get_slide_tile_invalid(slide_id, tile_x, level, expected_response):

    response = requests.get(f"http://localhost:8080/v1/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_x}")
    assert response.status_code == expected_response


@pytest.mark.parametrize("tile_size", [-1, 0, 1, 10000])
def test_get_region_maximum_extent(tile_size):

    level = 5
    start_x = 13
    start_y = 23
    slide_id = "45707118e3b55f1b8e03e1f19feee916"
    response = requests.get(
        f"http://localhost:8080/v1/slides/{slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{tile_size}/{tile_size}"
    )
    if tile_size * tile_size > 25000000:
        assert response.status_code == 403  # requested data too large
    elif tile_size <= 0:
        assert response.status_code == 422  # Unprocessable Entity
    else:
        assert response.status_code == 200
