import time

import pytest
import requests_mock
from wsi_service.models import SlideInfo
from wsi_service.tests.test_api_helpers import (
    client_changed_timeout,
    get_image,
    setup_mock,
)


@requests_mock.Mocker(real_http=True, kw="requests_mock")
def test_slide_source_timeout(client_changed_timeout, **kwargs):
    client = client_changed_timeout[0]
    slide_source = client_changed_timeout[1]
    setup_mock(kwargs)
    assert len(slide_source.opened_slides.keys()) == 0
    assert len(slide_source.slide_map.keys()) == 0
    response = client.get("/slides/b465382a4db159d2b7c8da5c917a2280/info")
    assert response.status_code == 200
    assert len(slide_source.opened_slides.keys()) == 1
    assert len(slide_source.slide_map.keys()) == 1
    time.sleep(0.5)
    assert len(slide_source.opened_slides.keys()) == 1
    assert len(slide_source.slide_map.keys()) == 1
    time.sleep(1.0)
    assert len(slide_source.opened_slides.keys()) == 0
    assert len(slide_source.slide_map.keys()) == 0
