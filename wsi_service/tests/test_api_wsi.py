import pytest
import requests_mock

from wsi_service.models.slide import SlideInfo
from wsi_service.settings import Settings
from wsi_service.tests.test_api_helpers import client, get_image, setup_mock


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "slide_id, num_levels, pixel_size_nm, tile_size, x, y",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", 12, 50, (128, 128), 46000, 32914),  # tiff
        ("f863c2ef155654b1af0387acc7ebdb60", 7, 499, (256, 256), 46000, 32914),  # svs
        (
            "c801ce3d1de45f2996e6a07b2d449bca",
            15,
            227,
            (4096, 8),
            122880,
            110592,
        ),  # ndpi
        (
            "7304006194f8530b9e19df1310a3670f",
            12,
            234,
            (256, 256),
            101832,
            219976,
        ),  # mrxs
    ],
)
def test_get_slide_info_valid(client, slide_id, num_levels, pixel_size_nm, tile_size, x, y, **kwargs):
    setup_mock(kwargs)
    response = client.get(f"/v1/slides/{slide_id}/info")
    assert response.status_code == 200
    slide_info = SlideInfo.parse_obj(response.json())
    assert slide_info.num_levels == num_levels
    assert round(slide_info.pixel_size_nm.x) == pixel_size_nm
    assert round(slide_info.pixel_size_nm.y) == pixel_size_nm
    assert slide_info.extent.x == x
    assert slide_info.extent.y == y
    assert slide_info.tile_extent.x == tile_size[0]
    assert slide_info.tile_extent.y == tile_size[1]


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [
        ("jpeg", 90),
        ("jpeg", 95),
        ("png", 0),
        ("png", 1),
        ("bmp", 0),
        ("gif", 0),
        ("tiff", 0),
    ],
)
@pytest.mark.parametrize(
    "slide_id, return_value, testpixel",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", 200, (247, 250, 249)),
        ("f863c2ef155654b1af0387acc7ebdb60", 200, (244, 249, 247)),
        ("c801ce3d1de45f2996e6a07b2d449bca", 200, (211, 199, 221)),
        ("7304006194f8530b9e19df1310a3670f", 200, (227, 155, 217)),
    ],
)
def test_get_slide_thumbnail_valid(
    client,
    image_format,
    image_quality,
    slide_id,
    return_value,
    testpixel,
    **kwargs,
):
    setup_mock(kwargs)
    max_size_x = 21
    max_size_y = 22
    response = client.get(
        f"/v1/slides/{slide_id}/thumbnail/max_size/{max_size_x}/{max_size_y}?image_format={image_format}&image_quality={image_quality}",
        stream=True,
    )
    assert response.status_code == return_value
    assert response.headers["content-type"] == f"image/{image_format}"
    image = get_image(response)
    x, y = image.size
    assert (x == max_size_x) or (y == max_size_y)
    if image_format in ["png", "bmp", "tiff"]:
        assert image.getpixel((5, 5)) == testpixel


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [
        ("jpeg", 90),
        ("jpeg", 95),
        ("png", 0),
        ("png", 1),
        ("bmp", 0),
        ("gif", 0),
        ("tiff", 0),
    ],
)
@pytest.mark.parametrize(
    "slide_id, has_label",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", False),
        ("f863c2ef155654b1af0387acc7ebdb60", True),
        ("c801ce3d1de45f2996e6a07b2d449bca", False),
        ("7304006194f8530b9e19df1310a3670f", True),
    ],
)
def test_get_slide_label_valid(client, image_format, image_quality, slide_id, has_label, **kwargs):
    setup_mock(kwargs)
    response = client.get(
        f"/v1/slides/{slide_id}/label?image_format={image_format}&image_quality={image_quality}",
        stream=True,
    )
    if has_label:
        assert response.status_code == 200
        assert response.headers["content-type"] == f"image/{image_format}"
        image = get_image(response)
        if image_format in ["png", "bmp", "tiff"] and slide_id in [
            "4b0ec5e0ec5e5e05ae9e500857314f20",
            "f863c2ef155654b1af0387acc7ebdb60",
            "c801ce3d1de45f2996e6a07b2d449bca",
        ]:
            image.thumbnail((1, 1))
            assert image.getpixel((0, 0)) == (126, 91, 50)
    else:
        assert response.status_code == 404


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [
        ("jpeg", 90),
        ("jpeg", 95),
        ("png", 0),
        ("png", 1),
        ("bmp", 0),
        ("gif", 0),
        ("tiff", 0),
    ],
)
@pytest.mark.parametrize(
    "slide_id, return_value, testpixel",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", 404, ()),
        ("f863c2ef155654b1af0387acc7ebdb60", 200, (178, 181, 179)),
        ("c801ce3d1de45f2996e6a07b2d449bca", 200, (200, 196, 198)),
        ("7304006194f8530b9e19df1310a3670f", 200, (211, 211, 211)),
    ],
)
def test_get_slide_macro_valid(
    client,
    image_format,
    image_quality,
    slide_id,
    return_value,
    testpixel,
    **kwargs,
):
    setup_mock(kwargs)
    response = client.get(
        f"/v1/slides/{slide_id}/macro?image_format={image_format}&image_quality={image_quality}",
        stream=True,
    )
    assert response.status_code == return_value
    if return_value == 200:
        assert response.headers["content-type"] == f"image/{image_format}"
        image = get_image(response)
        if image_format in ["png", "bmp", "tiff"]:
            image.thumbnail((1, 1))
            assert image.getpixel((0, 0)) == testpixel


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [
        ("jpeg", 90),
        ("jpeg", 95),
        ("png", 0),
        ("png", 1),
        ("bmp", 0),
        ("gif", 0),
        ("tiff", 0),
    ],
)
@pytest.mark.parametrize(
    "slide_id,  testpixel, start_x, start_y, size",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", (223, 217, 222), 15000, 15000, 345),
        ("f863c2ef155654b1af0387acc7ebdb60", (223, 217, 222), 15000, 15000, 345),
        ("c801ce3d1de45f2996e6a07b2d449bca", (218, 217, 225), 15000, 15000, 345),
        ("7304006194f8530b9e19df1310a3670f", (221, 170, 219), 50000, 90000, 345),
    ],
)
def test_get_slide_region_valid(
    client,
    image_format,
    image_quality,
    slide_id,
    testpixel,
    start_x,
    start_y,
    size,
    **kwargs,
):
    setup_mock(kwargs)
    level = 0
    size_x = size
    size_y = size + 198
    response = client.get(
        f"/v1/slides/{slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}?image_format={image_format}&image_quality={image_quality}",
        stream=True,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == f"image/{image_format}"
    image = get_image(response)
    x, y = image.size
    assert (x == size_x) or (y == size_y)
    if image_format in ["png", "bmp", "tiff"]:
        image.thumbnail((1, 1))
        assert image.getpixel((0, 0)) == testpixel


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "slide_id,  testpixel, start_x, start_y, size",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", (223, 217, 222), 15000, 15000, 30045),
        ("f863c2ef155654b1af0387acc7ebdb60", (223, 217, 222), 15000, 15000, 30045),
        ("c801ce3d1de45f2996e6a07b2d449bca", (218, 217, 225), 15000, 15000, 30045),
        ("7304006194f8530b9e19df1310a3670f", (221, 170, 219), 50000, 90000, 30045),
    ],
)
def test_get_slide_region_invalid(
    client,
    slide_id,
    testpixel,
    start_x,
    start_y,
    size,
    **kwargs,
):
    setup_mock(kwargs)
    level = 0
    size_x = size
    size_y = size + 198
    response = client.get(
        f"/v1/slides/{slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}",
        stream=True,
    )
    assert response.status_code == 403


import timeit


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "slide_id,  tile_x, tile_y, level",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", 1, 1, 11),
        ("f863c2ef155654b1af0387acc7ebdb60", 1, 1, 6),
        ("c801ce3d1de45f2996e6a07b2d449bca", 1, 1, 12),
        ("7304006194f8530b9e19df1310a3670f", 1, 1, 11),
    ],
)
def test_get_slide_tile_timing(
    client,
    slide_id,
    tile_x,
    tile_y,
    level,
    **kwargs,
):
    setup_mock(kwargs)
    tic = timeit.default_timer()
    response = client.get(
        f"/v1/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}",
        stream=True,
    )
    assert response.status_code == 200
    get_image(response)
    toc = timeit.default_timer()
    assert toc - tic < 2


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [
        ("jpeg", 90),
        ("jpeg", 95),
        ("png", 0),
        ("png", 1),
        ("bmp", 0),
        ("gif", 0),
        ("tiff", 0),
    ],
)
@pytest.mark.parametrize(
    "slide_id,  testpixel, tile_x, tile_y, tile_size",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", (243, 243, 243), 21, 22, (128, 128)),
        ("f863c2ef155654b1af0387acc7ebdb60", (246, 246, 246), 21, 22, (256, 256)),
        ("c801ce3d1de45f2996e6a07b2d449bca", (137, 143, 140), 21, 22, (4096, 8)),
        ("7304006194f8530b9e19df1310a3670f", (255, 255, 255), 60, 60, (256, 256)),
    ],
)
def test_get_slide_tile_valid(
    client,
    image_format,
    image_quality,
    slide_id,
    testpixel,
    tile_x,
    tile_y,
    tile_size,
    **kwargs,
):
    setup_mock(kwargs)
    level = 0
    response = client.get(
        f"/v1/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}?image_format={image_format}&image_quality={image_quality}",
        stream=True,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == f"image/{image_format}"
    image = get_image(response)
    x, y = image.size
    assert (x == tile_size[0]) or (y == tile_size[1])
    if image_format in ["png", "bmp", "tiff"]:
        image.thumbnail((1, 1))
        assert image.getpixel((0, 0)) == testpixel


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "slide_id",
    [
        "4b0ec5e0ec5e5e05ae9e500857314f20",
    ],
)
@pytest.mark.parametrize(
    "tile_x, level, expected_response",
    [
        (10, 1, 200),  # ok
        (10, 0, 200),  # ok
        (10, -1, 422),  # level -1 fails
        (10, 11, 200),  # level 15 ist coarsest level
        (10, 16, 422),  # level fails
    ],
)
def test_get_slide_tile_invalid(
    client,
    slide_id,
    tile_x,
    level,
    expected_response,
    **kwargs,
):
    setup_mock(kwargs)
    response = client.get(
        f"/v1/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_x}",
        stream=True,
    )
    assert response.status_code == expected_response


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "tile_size",
    [-1, 0, 1, 2500, 2501, 5000, 10000],
)
def test_get_region_maximum_extent(
    client,
    tile_size,
    **kwargs,
):
    wsi_settings = Settings()
    setup_mock(kwargs)
    level = 5
    start_x = 13
    start_y = 23
    slide_id = "7304006194f8530b9e19df1310a3670f"
    response = client.get(
        f"/v1/slides/{slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{tile_size}/{tile_size}",
        stream=True,
    )
    if tile_size * tile_size > wsi_settings.max_returned_region_size:
        assert response.status_code == 403  # requested data too large
    elif tile_size <= 0:
        assert response.status_code == 422  # Unprocessable Entity
    else:
        assert response.status_code == 200
