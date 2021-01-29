import os

from wsi_service.tests.test_api_helpers import (
    client,
    client_invalid_data_dir,
    client_no_data,
)


def test_get_cases_valid(client):
    response = client.get("/v1/cases/")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 9
    assert len(cases[0].keys()) == 3
    case = list(filter(lambda case: case["local_case_id"] == "Olympus", cases))[0]
    assert case["case_id"] == "7a32e2c36ca756d9b7df0b627ace4c12"


def test_get_available_slides_valid(client):
    response = client.get("/v1/cases/4593f30c39d75d2385c6c8811c4ae7e0/slides/")
    assert response.status_code == 200
    slides = response.json()
    slide = list(
        filter(
            lambda slide: slide["slide_storage"]["storage_addresses"][0]["address"].endswith("CMU-1.svs"),
            slides,
        )
    )[0]
    assert len(slides) == 1
    assert len(slides[0].keys()) == 3
    assert slide["slide_id"] == "f863c2ef155654b1af0387acc7ebdb60"
    assert slide["local_slide_id"] == "CMU-1.svs"
    assert slide["slide_storage"]["slide_id"] == "f863c2ef155654b1af0387acc7ebdb60"
    assert slide["slide_storage"]["storage_type"] == "fs"
    assert slide["slide_storage"]["storage_addresses"][0]["main_address"] == True
    assert slide["slide_storage"]["storage_addresses"][0]["storage_address_id"] == "89262a18eff45876b8aa45c42c334864"
    assert slide["slide_storage"]["storage_addresses"][0]["address"].endswith("Aperio/CMU-1.svs")
    assert slide["slide_storage"]["storage_addresses"][0]["slide_id"] == "f863c2ef155654b1af0387acc7ebdb60"


def test_get_slide_valid(client):
    response = client.get("/v1/slides/4b0ec5e0ec5e5e05ae9e500857314f20")
    assert response.status_code == 200
    slide = response.json()
    assert len(slide.keys()) == 3
    assert slide["slide_id"] == "4b0ec5e0ec5e5e05ae9e500857314f20"
    assert slide["local_slide_id"] == "CMU-1.tiff"
    assert slide["slide_storage"]["slide_id"] == "4b0ec5e0ec5e5e05ae9e500857314f20"
    assert slide["slide_storage"]["storage_type"] == "fs"
    assert slide["slide_storage"]["storage_addresses"][0]["main_address"] == True
    assert slide["slide_storage"]["storage_addresses"][0]["storage_address_id"] == "ed917cbb17ab54ee84152ba30adfb4d5"
    assert slide["slide_storage"]["storage_addresses"][0]["address"].endswith("Generic TIFF/CMU-1.tiff")
    assert slide["slide_storage"]["storage_addresses"][0]["slide_id"] == "4b0ec5e0ec5e5e05ae9e500857314f20"


def test_get_cases_no_data(client_no_data):
    response = client_no_data.get("/v1/cases/")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 0


def test_get_cases_two_empty_cases(client_no_data):
    os.mkdir(os.path.join(os.environ["data_dir"], "case0"))
    os.mkdir(os.path.join(os.environ["data_dir"], "case1"))
    response = client_no_data.get("/v1/cases/")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 2


def test_get_available_slides_empty_case(client_no_data):
    os.mkdir(os.path.join(os.environ["data_dir"], "case0"))
    response = client_no_data.get("/v1/cases/")
    assert response.status_code == 200
    cases = response.json()
    case_id = cases[0]["case_id"]
    response = client_no_data.get(f"/v1/cases/{case_id}/slides/")
    assert response.status_code == 200
    slides = response.json()
    assert len(slides) == 0


def test_get_available_slides_invalid_case_id(client):
    response = client.get("/v1/cases/invalid_id/slides/")
    assert response.status_code == 400
    assert response.json()["detail"] == "Case with case_id invalid_id does not exist"


def test_get_slide_invalid_slide_id(client):
    response = client.get("/v1/slides/invalid_id")
    assert response.status_code == 400
    assert response.json()["detail"] == "Slide with slide_id invalid_id does not exist"


def test_get_case_invalid_dir(client_invalid_data_dir):
    response = client_invalid_data_dir.get("/v1/cases/")
    assert response.status_code == 404
    assert response.json()["detail"] == "No such directory: /data/non_existing_dir"
