import os
import shutil
from importlib import reload

import pytest
from fastapi.testclient import TestClient

from wsi_service.__main__ import load_example_data


def setup_environment_variables():
    test_folder = os.path.dirname(os.path.realpath(__file__))
    os.environ["data_dir"] = os.path.join(test_folder, 'data/')
    os.environ["local_mode"] = str(True)
    os.environ["mapper_address"] = "http://localhost:8080/slides/{global_slide_id}"


def get_client():
    import wsi_service.api
    reload(wsi_service.api)
    return TestClient(wsi_service.api.api)


@pytest.fixture()
def client():
    setup_environment_variables()
    if not os.path.exists(os.environ["data_dir"]):
        os.mkdir(os.environ["data_dir"])
    load_example_data(os.path.join(os.environ["data_dir"], 'example'))
    yield get_client()


@pytest.fixture()
def client_no_data():
    setup_environment_variables()
    data_dir = os.environ['data_dir']
    del os.environ['data_dir']
    os.environ["data_dir"] = os.path.join(data_dir, 'empty')
    if not os.path.exists(os.environ["data_dir"]):
        os.mkdir(os.environ["data_dir"])
    yield get_client()
    shutil.rmtree(os.environ["data_dir"])


def test_get_cases_valid(client):
    response = client.get("/cases/")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 1
    assert len(cases[0].keys()) == 2
    assert cases[0]["global_case_id"] == "f8b723230e405a08bd7f039dfb85a9b2"
    assert cases[0]["local_case_id"] == "example"


def test_get_available_slides_valid(client):
    response = client.get("/cases/f8b723230e405a08bd7f039dfb85a9b2/slides/")
    assert response.status_code == 200
    slides = response.json()
    assert len(slides) == 1
    assert len(slides[0].keys()) == 5
    assert slides[0]["global_slide_id"] == "b465382a4db159d2b7c8da5c917a2280"
    assert slides[0]["global_case_id"] == "f8b723230e405a08bd7f039dfb85a9b2"
    assert slides[0]["local_slide_id"] == "CMU-1"
    assert slides[0]["storage_type"] == "fs"
    assert slides[0]["storage_address"].endswith('example/CMU-1.svs')


def test_get_slide_valid(client):
    response = client.get("/slides/b465382a4db159d2b7c8da5c917a2280")
    assert response.status_code == 200
    slide = response.json()
    assert len(slide.keys()) == 5
    assert slide["global_slide_id"] == "b465382a4db159d2b7c8da5c917a2280"
    assert slide["global_case_id"] == "f8b723230e405a08bd7f039dfb85a9b2"
    assert slide["local_slide_id"] == "CMU-1"
    assert slide["storage_type"] == "fs"
    assert slide["storage_address"].endswith('example/CMU-1.svs')


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


def test_get_available_slides_empy_case(client_no_data):
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
    assert response.json()["detail"] == "Case with global_case_id invalid_id does not exist"


def test_get_slide_invalid_global_slide_id(client):
    response = client.get("/slides/invalid_id")
    assert response.status_code == 400
    assert response.json()["detail"] == "Slide with global_slide_id invalid_id does not exist"
