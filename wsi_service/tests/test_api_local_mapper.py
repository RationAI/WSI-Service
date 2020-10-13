import os

from wsi_service.tests.test_api_helpers import client, client_no_data


def test_get_cases_valid(client):
    response = client.get("/cases/")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 9
    assert len(cases[0].keys()) == 2
    case = list(filter(lambda case: case["local_case_id"] == "Olympus", cases))[0]
    assert case["global_case_id"] == "7a32e2c36ca756d9b7df0b627ace4c12"


def test_get_available_slides_valid(client):
    response = client.get("/cases/4593f30c39d75d2385c6c8811c4ae7e0/slides/")
    assert response.status_code == 200
    slides = response.json()
    slide = list(filter(lambda slide: slide["local_slide_id"] == "CMU-1.svs", slides))[
        0
    ]
    assert len(slides) == 1
    assert len(slides[0].keys()) == 5
    assert slide["global_slide_id"] == "f863c2ef155654b1af0387acc7ebdb60"
    assert slide["global_case_id"] == "4593f30c39d75d2385c6c8811c4ae7e0"
    assert slide["local_slide_id"] == "CMU-1.svs"
    assert slide["storage_type"] == "fs"
    assert slide["storage_address"].endswith("Aperio/CMU-1.svs")


def test_get_slide_valid(client):
    response = client.get("/slides/4b0ec5e0ec5e5e05ae9e500857314f20")
    assert response.status_code == 200
    slide = response.json()
    assert len(slide.keys()) == 5
    assert slide["global_slide_id"] == "4b0ec5e0ec5e5e05ae9e500857314f20"
    assert slide["global_case_id"] == "491e1f7180445b1e805cdc128ba884b7"
    assert slide["local_slide_id"] == "CMU-1.tiff"
    assert slide["storage_type"] == "fs"
    assert slide["storage_address"].endswith("Generic TIFF/CMU-1.tiff")


def test_get_cases_no_data(client_no_data):
    response = client_no_data.get("/cases/")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 0


def test_get_cases_two_empty_cases(client_no_data):
    os.mkdir(os.path.join(os.environ["data_dir"], "case0"))
    os.mkdir(os.path.join(os.environ["data_dir"], "case1"))
    response = client_no_data.get("/cases/")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 2


def test_get_available_slides_empty_case(client_no_data):
    os.mkdir(os.path.join(os.environ["data_dir"], "case0"))
    response = client_no_data.get("/cases/")
    assert response.status_code == 200
    cases = response.json()
    global_case_id = cases[0]["global_case_id"]
    response = client_no_data.get(f"/cases/{global_case_id}/slides/")
    assert response.status_code == 200
    slides = response.json()
    assert len(slides) == 0


def test_get_available_slides_invalid_global_case_id(client):
    response = client.get("/cases/invalid_id/slides/")
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Case with global_case_id invalid_id does not exist"
    )


def test_get_slide_invalid_global_slide_id(client):
    response = client.get("/slides/invalid_id")
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Slide with global_slide_id invalid_id does not exist"
    )
