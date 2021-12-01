import asyncio

import pytest
from fastapi.exceptions import HTTPException

from wsi_service.tests.unit.test_client import get_client_and_slide_manager


@pytest.mark.asyncio
async def test_slide_manager_timeout(aioresponses):
    aioresponses.get(
        "http://testserver/slides/750129436e215175beb6c979bd9bfa50",
        status=200,
        payload={
            "slide_id": "750129436e215175beb6c979bd9bfa50",
            "storage_type": "fs",
            "storage_addresses": [
                {
                    "address": "testcase/CMU-1-small.tiff",
                    "main_address": True,
                    "storage_address_id": "8d32dba05a4558218880f06caf30d3ac",
                    "slide_id": "750129436e215175beb6c979bd9bfa50",
                }
            ],
        },
    )
    _, slide_manager = get_client_and_slide_manager()
    slide_manager.close()
    slide_manager.timeout = 1
    assert len(slide_manager.slide_cache.get_all()) == 0
    await slide_manager.get_slide("750129436e215175beb6c979bd9bfa50")
    assert len(slide_manager.slide_cache.get_all()) == 1
    await asyncio.sleep(0.5)
    assert len(slide_manager.slide_cache.get_all()) == 1
    await asyncio.sleep(1.0)
    assert len(slide_manager.slide_cache.get_all()) == 0


@pytest.mark.asyncio
async def test_slide_manager_unknown():
    _, slide_manager = get_client_and_slide_manager()
    try:
        await slide_manager.get_slide("unavailable")
    except HTTPException as e:
        assert e.status_code == 503
