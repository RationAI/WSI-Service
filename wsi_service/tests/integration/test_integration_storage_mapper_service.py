import json
import time

import pytest
import requests


def check_storage_mapper_is_available():
    available = False
    for _ in range(10):
        try:
            r = requests.get("http://storage-mapper-service:8000/alive")
            if r.json()["status"] == "ok":
                available = True
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.5)
    return available


@pytest.mark.parametrize("api_version", ["v1", "v3"])
@pytest.mark.parametrize("slide_id", ["8d32dba05a4558218880f06caf30d3ac"])
def test_real_storage_mapper_with_wsi_service(api_version, slide_id):
    available = check_storage_mapper_is_available()
    if available:
        # create storage mapper info
        slide_storage = {
            "slide_id": slide_id,
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "Aperio/CMU-1.svs",
                    "slide_id": slide_id,
                    "main_address": True,
                    "storage_address_id": slide_id,
                }
            ],
        }
        r = requests.post(f"http://storage-mapper-service:8000/{api_version}/slides/", data=json.dumps(slide_storage))
        assert r.status_code in [201, 409]
    r = requests.get(f"http://localhost:8080/{api_version}/slides/{slide_id}/info")
    assert r.status_code == 200
    assert r.json()["id"] == slide_id
