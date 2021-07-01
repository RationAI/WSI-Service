import pytest
import requests_mock

from wsi_service.tests.unit.test_client import get_client_and_slide_manager, setup_storage_mapper_mock


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
@requests_mock.Mocker(real_http=True, kw="requests_mock")
def test_endpoints(url, status_code, **kwargs):
    setup_storage_mapper_mock(kwargs)
    client, slide_manager = get_client_and_slide_manager()
    r = client.get(url)
    slide_manager.close()
    assert r.status_code == status_code
