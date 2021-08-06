import pytest

from wsi_service.tests.unit.test_client import get_client_and_slide_manager


@pytest.mark.parametrize(
    "url, status_code",
    [
        # general endpoints
        ("/alive", 200),
        ("/v1/slides/fc1ef3789eac548883e9923455608e13/info", 200),
        ("/v1/slides/fc1ef3789eac548883e9923455608e13/thumbnail/max_size/1/1", 200),
        ("/v1/slides/fc1ef3789eac548883e9923455608e13/label/max_size/1/1", 404),
        ("/v1/slides/fc1ef3789eac548883e9923455608e13/macro/max_size/1/1", 404),
        ("/v1/slides/fc1ef3789eac548883e9923455608e13/region/level/0/start/0/0/size/1/1", 200),
        ("/v1/slides/fc1ef3789eac548883e9923455608e13/tile/level/0/tile/0/0", 200),
        # local mode endpoints
        ("/v1/cases/", 200),
        ("/v1/cases/b85c8c5b3959522ca49b013c000078cc/slides", 200),
        ("/v1/slides/fc1ef3789eac548883e9923455608e13", 200),
        ("/v1/slides/fc1ef3789eac548883e9923455608e13/storage", 200),
        ("/v1/slides/fc1ef3789eac548883e9923455608e13/viewer", 200),
        ("/v1/validation_viewer", 200),
    ],
)
def test_endpoints(aioresponses, url, status_code):
    aioresponses.get(
        "http://testserver/slides/fc1ef3789eac548883e9923455608e13",
        status=200,
        payload={
            "slide_id": "fc1ef3789eac548883e9923455608e13",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "testcase/CMU-1-small.tiff",
                    "main_address": True,
                    "storage_address_id": "f863c2ef155654b1af0387acc7ebdb60",
                    "slide_id": "fc1ef3789eac548883e9923455608e13",
                }
            ],
        },
    )
    client, _ = get_client_and_slide_manager()
    r = client.get(url)
    assert r.status_code == status_code
