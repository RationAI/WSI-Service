import os

import requests

from wsi_service.tests.api.test_api_helpers import (
    client_invalid_data_dir,
    client_no_data,
)


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


def test_get_case_invalid_dir(client_invalid_data_dir):
    response = client_invalid_data_dir.get("/v1/cases/")
    assert response.status_code == 404
    assert response.json()["detail"] == "No such directory: /data/non_existing_dir"
