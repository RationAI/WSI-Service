import requests

from wsi_service.tests.integration.test_integration_helper import (
    copy_env,
    docker_compose_file,
    modify_ports_in_test_env,
    wsi_service,
)


def test_alive(wsi_service):
    response = requests.get(f"{wsi_service}/alive")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_cases_valid(wsi_service):
    response = requests.get(f"{wsi_service}/v1/cases/")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 11
    assert len(cases[0].keys()) == 3
    case = list(filter(lambda case: case["local_case_id"] == "Olympus", cases))[0]
    assert case["case_id"] == "7a32e2c36ca756d9b7df0b627ace4c12"


def test_get_available_slides_valid(wsi_service):
    response = requests.get(f"{wsi_service}/v1/cases/4593f30c39d75d2385c6c8811c4ae7e0/slides/")
    assert response.status_code == 200
    slides = response.json()
    slide = list(
        filter(lambda slide: slide["slide_storage"]["storage_addresses"][0]["address"].endswith("CMU-1.svs"), slides)
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


def test_get_slide_valid(wsi_service):
    response = requests.get(f"{wsi_service}/v1/slides/4b0ec5e0ec5e5e05ae9e500857314f20")
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


def test_get_available_slides_invalid_case_id(wsi_service):
    response = requests.get(f"{wsi_service}/v1/cases/invalid_id/slides/")
    assert response.status_code == 400
    assert response.json()["detail"] == "Case with case_id invalid_id does not exist"


def test_get_slide_invalid_slide_id(wsi_service):
    response = requests.get(f"{wsi_service}/v1/slides/invalid_id")
    assert response.status_code == 400
    assert response.json()["detail"] == "Slide with slide_id invalid_id does not exist"
