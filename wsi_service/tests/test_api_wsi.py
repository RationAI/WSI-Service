
import os

import requests
import requests_mock
from wsi_service.tests.test_api_helpers import client, client_no_data
from wsi_service.models import SlideInfo


@requests_mock.Mocker(real_http=True, kw='requests_mock')
def test_url(client, **kwargs):
    mock = kwargs['requests_mock']
    mock.get('http://testserver/slides/b465382a4db159d2b7c8da5c917a2280', 
        json={
            'global_slide_id': 'b465382a4db159d2b7c8da5c917a2280', 
            'global_case_id': 'f8b723230e405a08bd7f039dfb85a9b2', 
            'local_slide_id': 'CMU-1', 
            'storage_type': 'fs', 
            'storage_address': 'example/CMU-1.svs'
        }
    )
    response = client.get("/slides/b465382a4db159d2b7c8da5c917a2280/info")
    slide_info = SlideInfo.parse_obj(response.json())
    assert slide_info.num_levels == 16
    assert slide_info.pixel_size_nm == 499
    assert slide_info.extent.x == 46000
    assert slide_info.extent.y == 32914
    assert slide_info.tile_extent.x == 512
    assert slide_info.tile_extent.y == 512
