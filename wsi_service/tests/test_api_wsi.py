import pytest
import requests_mock
from wsi_service.models import SlideInfo
from wsi_service.tests.test_api_helpers import client, get_image, setup_mock


@requests_mock.Mocker(real_http=True, kw="requests_mock")
def test_get_slide_info_valid(client, **kwargs):
    setup_mock(kwargs)
    response = client.get("/slides/b465382a4db159d2b7c8da5c917a2280/info")
    assert response.status_code == 200
    slide_info = SlideInfo.parse_obj(response.json())
    assert slide_info.num_levels == 16
    assert slide_info.pixel_size_nm == 499
    assert slide_info.extent.x == 46000
    assert slide_info.extent.y == 32914
    assert slide_info.tile_extent.x == 512
    assert slide_info.tile_extent.y == 512


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [("jpeg", 90), ("jpeg", 95), ("png", 0), ("bmp", 0), ("gif", 0), ("tiff", 0)],
)
def test_get_slide_thumbnail_valid(client, image_format, image_quality, **kwargs):
    setup_mock(kwargs)
    max_size_x = 21
    max_size_y = 22
    response = client.get(
        f"/slides/b465382a4db159d2b7c8da5c917a2280/thumbnail/max_size/{max_size_x}/{max_size_y}?image_format={image_format}&image_quality={image_quality}",
        stream=True,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == f"image/{image_format}"
    image = get_image(response)
    x, y = image.size
    assert (x == max_size_x) or (y == max_size_y)
    if image_format in ["png", "bmp", "tiff"]:
        assert image.getpixel((10, 10)) == (248, 252, 249)


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [("jpeg", 90), ("jpeg", 95), ("png", 0), ("bmp", 0), ("gif", 0), ("tiff", 0)],
)
def test_get_slide_label_valid(client, image_format, image_quality, **kwargs):
    setup_mock(kwargs)
    response = client.get(
        f"/slides/b465382a4db159d2b7c8da5c917a2280/label?image_format={image_format}&image_quality={image_quality}",
        stream=True,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == f"image/{image_format}"
    image = get_image(response)
    if image_format in ["png", "bmp", "tiff"]:
        image.thumbnail((1, 1))
        assert image.getpixel((0, 0)) == (126, 91, 50)


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [("jpeg", 90), ("jpeg", 95), ("png", 0), ("bmp", 0), ("gif", 0), ("tiff", 0)],
)
def test_get_slide_macro_valid(client, image_format, image_quality, **kwargs):
    setup_mock(kwargs)
    response = client.get(
        f"/slides/b465382a4db159d2b7c8da5c917a2280/macro?image_format={image_format}&image_quality={image_quality}",
        stream=True,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == f"image/{image_format}"
    image = get_image(response)
    if image_format in ["png", "bmp", "tiff"]:
        image.thumbnail((1, 1))
        assert image.getpixel((0, 0)) == (178, 181, 179)


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [("jpeg", 90), ("jpeg", 95), ("png", 0), ("bmp", 0), ("gif", 0), ("tiff", 0)],
)
def test_get_slide_region_valid(client, image_format, image_quality, **kwargs):
    setup_mock(kwargs)
    level = 0
    start_x = 15000
    start_y = 15000
    size_x = 345
    size_y = 543
    response = client.get(
        f"/slides/b465382a4db159d2b7c8da5c917a2280/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}?image_format={image_format}&image_quality={image_quality}",
        stream=True,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == f"image/{image_format}"
    image = get_image(response)
    x, y = image.size
    assert (x == size_x) or (y == size_y)
    if image_format in ["png", "bmp", "tiff"]:
        image.thumbnail((1, 1))
        assert image.getpixel((0, 0)) == (223, 217, 222)


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [("jpeg", 90), ("jpeg", 95), ("png", 0), ("bmp", 0), ("gif", 0), ("tiff", 0)],
)
def test_get_slide_tile_valid(client, image_format, image_quality, **kwargs):
    setup_mock(kwargs)
    level = 0
    tile_x = 21
    tile_y = 22
    response = client.get(
        f"/slides/b465382a4db159d2b7c8da5c917a2280/tile/level/{level}/tile/{tile_x}/{tile_y}?image_format={image_format}&image_quality={image_quality}",
        stream=True,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == f"image/{image_format}"
    image = get_image(response)
    x, y = image.size
    assert (x == 512) or (y == 512)
    if image_format in ["png", "bmp", "tiff"]:
        image.thumbnail((1, 1))
        assert image.getpixel((0, 0)) == (246, 246, 246)
