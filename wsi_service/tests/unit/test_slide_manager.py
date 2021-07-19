import time

import requests_mock
from fastapi.exceptions import HTTPException

from wsi_service.tests.unit.test_client import get_client_and_slide_manager, setup_storage_mapper_mock


@requests_mock.Mocker(real_http=True, kw="requests_mock")
def test_slide_manager_timeout(**kwargs):
    setup_storage_mapper_mock(kwargs)
    _, slide_manager = get_client_and_slide_manager()
    slide_manager.close()
    slide_manager.timeout = 1
    assert len(slide_manager.opened_slides.keys()) == 0
    assert len(slide_manager.slide_map.keys()) == 0
    slide_manager.get_slide("fc1ef3789eac548883e9923455608e13")
    assert len(slide_manager.opened_slides.keys()) == 1
    assert len(slide_manager.slide_map.keys()) == 1
    time.sleep(0.5)
    assert len(slide_manager.opened_slides.keys()) == 1
    assert len(slide_manager.slide_map.keys()) == 1
    time.sleep(1.0)
    assert len(slide_manager.opened_slides.keys()) == 0
    assert len(slide_manager.slide_map.keys()) == 0


@requests_mock.Mocker(real_http=True, kw="requests_mock")
def test_slide_manager_unknown(**kwargs):
    setup_storage_mapper_mock(kwargs)
    _, slide_manager = get_client_and_slide_manager()
    try:
        slide_manager.get_slide("unavailable")
    except HTTPException as e:
        assert e.status_code == 503
