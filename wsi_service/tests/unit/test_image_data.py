import io

import pytest
from PIL import Image

from wsi_service.tests.unit.test_client import get_client_and_slide_manager


@pytest.mark.parametrize(
    "slide_id,address,plugin",
    [
        ("d97155a9b5355d92a14d896a3786d4c8", "testcase/mask_test.tif", "tiffslide"),
        ("d97155a9b5355d92a14d896a3786d4c8", "testcase/mask_test.tif", "openslide"),
        ("2a34343af6c75c01b2aa3d1a53e21f2e", "testcase/mask_test.jpeg", "pil"),
    ],
)
def test_masks(aioresponses, slide_id, address, plugin):
    aioresponses.get(
        f"http://testserver/slides/{slide_id}",
        status=200,
        payload={
            "slide_id": slide_id,
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": address,
                    "main_address": True,
                    "storage_address_id": slide_id,
                    "slide_id": slide_id,
                }
            ],
        },
    )
    client, _ = get_client_and_slide_manager()
    # get info
    r = client.get(f"/v3/slides/{slide_id}/info?plugin={plugin}")
    assert r.status_code == 200
    info = r.json()
    # get region
    size_x = info["extent"]["x"]
    size_y = info["extent"]["y"]
    r = client.get(f"/v3/slides/{slide_id}/region/level/0/start/0/0/size/{size_x}/{size_y}?plugin={plugin}")
    assert r.status_code == 200
    image = Image.open(r)
    assert image.mode == "RGB"
    assert image.size == (size_x, size_y)
    image.thumbnail((1, 1))
    avg_color = image.getpixel((0, 0))
    assert avg_color == (56, 56, 56)
