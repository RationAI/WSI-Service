import asyncio

import pytest
from fastapi.exceptions import HTTPException

from wsi_service.tests.unit.test_client import get_client_and_slide_manager


@pytest.mark.asyncio
async def test_slide_manager_timeout(aioresponses):
    aioresponses.get(
        "http://testserver/slides/fc1ef3789eac548883e9923455608e13",
        status=200,
        payload={
            "slide_id": "fc1ef3789eac548883e9923455608e13",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "/wsi-service/wsi_service/tests/unit/data/testcase/CMU-1-small.tiff",
                    "main_address": True,
                    "storage_address_id": "f863c2ef155654b1af0387acc7ebdb60",
                    "slide_id": "fc1ef3789eac548883e9923455608e13",
                }
            ],
        },
    )
    _, slide_manager = get_client_and_slide_manager()
    slide_manager.close()
    slide_manager.timeout = 1
    assert len(slide_manager.opened_slide_storages.keys()) == 0
    await slide_manager.get_slide("fc1ef3789eac548883e9923455608e13")
    assert len(slide_manager.opened_slide_storages.keys()) == 1
    await asyncio.sleep(0.5)
    assert len(slide_manager.opened_slide_storages.keys()) == 1
    await asyncio.sleep(1.0)
    assert len(slide_manager.opened_slide_storages.keys()) == 0


@pytest.mark.asyncio
async def test_slide_manager_unknown():
    _, slide_manager = get_client_and_slide_manager()
    try:
        await slide_manager.get_slide("unavailable")
    except HTTPException as e:
        assert e.status_code == 503
