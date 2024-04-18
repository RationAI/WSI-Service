import pytest

from wsi_service.tests.unit.test_client import get_client_and_slide_manager


@pytest.mark.parametrize(
    "url, status_code",
    [
        # root
        ("/alive", 200),
        # local mode endpoints
        ("/cases/", 200),
        ("/cases/b85c8c5b3959522ca49b013c000078cc/slides", 200),
        ("/slides/14b5c5dab96b540bba23b08429592bcf", 200),
        ("/slides/14b5c5dab96b540bba23b08429592bcf/storage", 200),
        ("/slides/14b5c5dab96b540bba23b08429592bcf/viewer", 200),
        ("/validation_viewer", 200),
        # v3
        ("/v3/slides/14b5c5dab96b540bba23b08429592bcf/info", 200),
        ("/v3/slides/14b5c5dab96b540bba23b08429592bcf/download", 200),
        ("/v3/slides/14b5c5dab96b540bba23b08429592bcf/thumbnail/max_size/1/1", 200),
        ("/v3/slides/14b5c5dab96b540bba23b08429592bcf/label/max_size/1/1", 404),
        ("/v3/slides/14b5c5dab96b540bba23b08429592bcf/macro/max_size/1/1", 404),
        ("/v3/slides/14b5c5dab96b540bba23b08429592bcf/region/level/0/start/0/0/size/1/1", 200),
        ("/v3/slides/14b5c5dab96b540bba23b08429592bcf/tile/level/0/tile/0/0", 200),
    ],
)
def test_endpoints(aioresponses, url, status_code):
    aioresponses.get(
        "http://testserver/slides/14b5c5dab96b540bba23b08429592bcf",
        status=200,
        payload={
            "slide_id": "14b5c5dab96b540bba23b08429592bcf",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "testcase/CMU-1-small.tiff",
                    "main_address": True,
                    "storage_address_id": "14b5c5dab96b540bba23b08429592bcf",
                    "slide_id": "14b5c5dab96b540bba23b08429592bcf",
                }
            ],
        },
    )
    client, _ = get_client_and_slide_manager()
    r = client.get(url)
    assert r.status_code == status_code
