import pytest
import requests_mock
import tifffile
from PIL import Image

from wsi_service.models.slide import SlideInfo
from wsi_service.settings import Settings
from wsi_service.tests.test_api_helpers import (
    client,
    get_image,
    get_tiff_image,
    setup_mock,
    tiff_pixels_equal,
)


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", 3, 8, 10, 50, (128, 128), 46000, 32914),  # tiff
        ("f863c2ef155654b1af0387acc7ebdb60", 3, 8, 3, 499, (256, 256), 46000, 32914),  # svs
        ("c801ce3d1de45f2996e6a07b2d449bca", 3, 8, 13, 227, (4096, 8), 122880, 110592),  # ndpi
        ("7304006194f8530b9e19df1310a3670f", 3, 8, 10, 234, (256, 256), 101832, 219976),  # mrxs
        ("46061cfc30a65acab7a1ed644771a340", 3, 16, 3, 325, (256, 256), 11260, 22300),  # ome-tif 3x16bit
        ("56ed11a2a9e95f87a1e466cf720ceffa", 5, 8, 6, 498, (512, 512), 24960, 34560),  # ome-tif 5x8bit
        ("cdad4692405c556ca63185bee512e95e", 3, 8, 10, 232, (256, 256), 114943, 76349),  # bif
        ("c4682788c7e85d739ce043b3f6eaff70", 3, 8, 6, 250, (256, 256), 106259, 306939),  # scn
    ],
)
def test_get_slide_info_valid(
    client, slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y, **kwargs
):
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
    assert len(slide_info.channels) == channels
    assert slide_info.channel_depth == channel_depth


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [("jpeg", 90), ("jpeg", 95), ("png", 0), ("png", 1), ("bmp", 0), ("gif", 0), ("tiff", 100)],
)
@pytest.mark.parametrize(
    "slide_id, return_value, pixel_location, testpixel_rgb, testpixel_multichannel",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", 200, (5, 5), (247, 250, 249), (247, 250, 249)),
        ("f863c2ef155654b1af0387acc7ebdb60", 200, (5, 5), (244, 249, 247), (244, 249, 247)),
        ("c801ce3d1de45f2996e6a07b2d449bca", 200, (5, 5), (211, 199, 221), (211, 199, 221)),
        ("7304006194f8530b9e19df1310a3670f", 200, (5, 5), (227, 155, 217), (227, 155, 217)),
        ("46061cfc30a65acab7a1ed644771a340", 200, (0, 0), (0, 0, 0), (3, 2, 0)),
        ("46061cfc30a65acab7a1ed644771a340", 200, (10, 10), (10, 6, 1), (675, 432, 121)),
        ("56ed11a2a9e95f87a1e466cf720ceffa", 200, (0, 0), (0, 0, 0), (0, 0, 0)),
        ("56ed11a2a9e95f87a1e466cf720ceffa", 200, (10, 10), (87, 51, 23), (5654, 3341, 1542)),
        ("cdad4692405c556ca63185bee512e95e", 200, (5, 5), (241, 241, 241), (241, 241, 241)),
        ("c4682788c7e85d739ce043b3f6eaff70", 200, (5, 5), (221, 212, 219), (221, 212, 219)),
    ],
)
def test_get_slide_thumbnail_valid(
    client,
    image_format,
    image_quality,
    slide_id,
    return_value,
    pixel_location,
    testpixel_rgb,
    testpixel_multichannel,
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
    if response.headers["content-type"] == "image/tiff":
        image = get_tiff_image(response)
        x, y = image.pages.keyframe.imagewidth, image.pages.keyframe.imagelength
        assert (x == max_size_x) or (y == max_size_y)
        narray = image.asarray()
        for i, pixel in enumerate(testpixel_multichannel):
            c = narray[i][pixel_location[0]][pixel_location[1]]
            assert c == pixel
    else:
        image = get_image(response)
        x, y = image.size
        assert (x == max_size_x) or (y == max_size_y)
        if image_format in ["png", "bmp"]:
            assert image.getpixel((pixel_location[0], pixel_location[1])) == testpixel_rgb


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [("jpeg", 90), ("jpeg", 95), ("png", 0), ("png", 1), ("bmp", 0), ("gif", 0), ("tiff", 100)],
)
@pytest.mark.parametrize(
    "slide_id, has_label, pixel_location, testpixel",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", False, (), ()),
        ("f863c2ef155654b1af0387acc7ebdb60", True, (0, 0), (0, 0, 0)),
        ("f863c2ef155654b1af0387acc7ebdb60", True, (104, 233), (216, 142, 66)),
        ("c801ce3d1de45f2996e6a07b2d449bca", False, (), ()),
        ("7304006194f8530b9e19df1310a3670f", True, (0, 0), (19, 19, 19)),
        ("7304006194f8530b9e19df1310a3670f", True, (200, 221), (222, 222, 222)),
        ("46061cfc30a65acab7a1ed644771a340", False, (), ()),
        ("56ed11a2a9e95f87a1e466cf720ceffa", False, (), ()),
        ("cdad4692405c556ca63185bee512e95e", False, (), ()),
        ("c4682788c7e85d739ce043b3f6eaff70", False, (), ()),
    ],
)
def test_get_slide_label_valid(
    client, image_format, image_quality, slide_id, has_label, pixel_location, testpixel, **kwargs
):
    setup_mock(kwargs)
    response = client.get(
        f"/v1/slides/{slide_id}/label?image_format={image_format}&image_quality={image_quality}", stream=True
    )
    if has_label:
        assert response.status_code == 200
        assert response.headers["content-type"] == f"image/{image_format}"
        if response.headers["content-type"] == "image/tiff":
            image = get_tiff_image(response)
            narray = image.asarray()
            for i, value in enumerate(testpixel):
                c = narray[i][pixel_location[1]][pixel_location[0]]
                assert c == value
        else:
            image = get_image(response)
            if image_format in ["png", "bmp"] and slide_id in [
                "4b0ec5e0ec5e5e05ae9e500857314f20",
                "f863c2ef155654b1af0387acc7ebdb60",
                "c801ce3d1de45f2996e6a07b2d449bca",
            ]:
                assert image.getpixel((pixel_location[0], pixel_location[1])) == testpixel
    else:
        assert response.status_code == 404


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [("jpeg", 90), ("jpeg", 95), ("png", 0), ("png", 1), ("bmp", 0), ("gif", 0), ("tiff", 100)],
)
@pytest.mark.parametrize(
    "slide_id, return_value, pixel_location, testpixel",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", 404, (), ()),
        ("f863c2ef155654b1af0387acc7ebdb60", 200, (0, 0), (0, 0, 0)),
        ("f863c2ef155654b1af0387acc7ebdb60", 200, (457, 223), (179, 149, 174)),
        ("c801ce3d1de45f2996e6a07b2d449bca", 200, (0, 0), (67, 67, 67)),
        ("c801ce3d1de45f2996e6a07b2d449bca", 200, (800, 65), (182, 155, 172)),
        ("7304006194f8530b9e19df1310a3670f", 200, (0, 0), (219, 219, 219)),
        ("7304006194f8530b9e19df1310a3670f", 200, (213, 438), (129, 129, 129)),
        ("46061cfc30a65acab7a1ed644771a340", 404, (), ()),
        ("56ed11a2a9e95f87a1e466cf720ceffa", 404, (), ()),
        ("cdad4692405c556ca63185bee512e95e", 200, (0, 0), (60, 51, 36)),
        ("c4682788c7e85d739ce043b3f6eaff70", 200, (0, 0), (3, 3, 3)),
    ],
)
def test_get_slide_macro_valid(
    client, image_format, image_quality, slide_id, return_value, pixel_location, testpixel, **kwargs
):
    setup_mock(kwargs)
    response = client.get(
        f"/v1/slides/{slide_id}/macro?image_format={image_format}&image_quality={image_quality}", stream=True
    )
    assert response.status_code == return_value
    if return_value == 200:
        if response.headers["content-type"] == "image/tiff":
            image = get_tiff_image(response)
            narray = image.asarray()
            for i, value in enumerate(testpixel):
                c = narray[i][pixel_location[1]][pixel_location[0]]
                assert c == value
        else:
            image = get_image(response)
            if image_format in ["png", "bmp"]:
                assert image.getpixel((pixel_location[0], pixel_location[1])) == testpixel


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [("jpeg", 100), ("png", 100), ("png", 100), ("bmp", 100), ("gif", 100), ("tiff", 100)],
)
@pytest.mark.parametrize(
    "slide_id,  pixel_location, testpixel, start_x, start_y, size",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", (0, 0), (255, 236, 253), 15000, 15000, 345),
        ("f863c2ef155654b1af0387acc7ebdb60", (0, 0), (255, 235, 255), 15000, 15000, 345),
        ("c801ce3d1de45f2996e6a07b2d449bca", (0, 0), (220, 219, 227), 15000, 15000, 345),
        ("7304006194f8530b9e19df1310a3670f", (0, 0), (231, 182, 212), 50000, 90000, 345),
        ("cdad4692405c556ca63185bee512e95e", (0, 0), (245, 241, 242), 30000, 30000, 345),
        ("c4682788c7e85d739ce043b3f6eaff70", (0, 0), (131, 59, 122), 50000, 55000, 345),
    ],
)
def test_get_slide_region_valid_brightfield(
    client, image_format, image_quality, slide_id, pixel_location, testpixel, start_x, start_y, size, **kwargs
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
    if response.headers["content-type"] == "image/tiff":
        image = get_tiff_image(response)
        x, y = image.pages.keyframe.imagewidth, image.pages.keyframe.imagelength
        assert (x == size_x) or (y == size_y)
        narray = image.asarray()
        r = narray[0][pixel_location[0]][pixel_location[1]]
        g = narray[1][pixel_location[0]][pixel_location[1]]
        b = narray[2][pixel_location[0]][pixel_location[1]]
        assert (r, g, b) == testpixel
    else:
        image = get_image(response)
        x, y = image.size
        assert (x == size_x) or (y == size_y)
        if image_format in ["png", "bmp"]:
            assert image.getpixel((pixel_location[0], pixel_location[1])) == testpixel


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize("image_format, image_quality", [("tiff", 100), ("jpeg", 90), ("png", 100), ("bmp", 100)])
@pytest.mark.parametrize(
    "slide_id, channels, start_point, size, pixel_location, testpixel_multichannel, testpixel_rgb",
    [
        ("46061cfc30a65acab7a1ed644771a340", 3, (0, 0), (256, 256), (0, 0), (0, 0, 0), (0, 0, 0)),
        ("46061cfc30a65acab7a1ed644771a340", 3, (512, 512), (256, 256), (100, 100), (3900, 2792, 3859), (60, 43, 60)),
        ("56ed11a2a9e95f87a1e466cf720ceffa", 5, (0, 0), (256, 256), (0, 0), (0, 0, 0), (0, 0, 0)),
        ("56ed11a2a9e95f87a1e466cf720ceffa", 5, (512, 512), (256, 256), (200, 200), (4, 0, 0), (4, 0, 0)),
    ],
)
def test_get_slide_region_valid_fluorescence(
    client,
    slide_id,
    channels,
    start_point,
    size,
    pixel_location,
    testpixel_multichannel,
    testpixel_rgb,
    image_format,
    image_quality,
    **kwargs,
):
    setup_mock(kwargs)
    level = 2
    response = client.get(
        f"/v1/slides/{slide_id}/region/level/{level}/start/{start_point[0]}/{start_point[1]}/size/{size[0]}/{size[1]}?image_format={image_format}&image_quality={image_quality}",
        stream=True,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == f"image/{image_format}"
    if response.headers["content-type"] == "image/tiff":
        image = get_tiff_image(response)
        assert image.pages.keyframe.shape[0] == channels
        x, y = image.pages.keyframe.imagewidth, image.pages.keyframe.imagelength
        assert (x == size[0]) or (y == size[1])
        narray = image.asarray()
        for i, value in enumerate(testpixel_multichannel):
            c = narray[i][pixel_location[0]][pixel_location[1]]
            assert c == value
    else:
        image = get_image(response)
        x, y = image.size
        assert (x == size[0]) or (y == size[1])
        if image_format in ["png", "bmp"]:
            assert image.getpixel((pixel_location[0], pixel_location[1])) == testpixel_rgb


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize("image_format, image_quality", [("png", 100), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, level, channels, start_point, size, pixel_location, testpixel_multichannel, testpixel_rgb",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", 7, [0], (0, 0), (256, 256), (128, 128), [246], (246, 0, 0)),
        ("46061cfc30a65acab7a1ed644771a340", 2, [0], (0, 0), (256, 256), (128, 128), [740], (13, 6, 0)),
        ("46061cfc30a65acab7a1ed644771a340", 2, [0, 1], (0, 0), (256, 256), (128, 128), [740, 525], (13, 9, 0)),
        ("56ed11a2a9e95f87a1e466cf720ceffa", 5, [0], (0, 0), (256, 256), (128, 128), [36], (0, 0, 70)),
        (
            "56ed11a2a9e95f87a1e466cf720ceffa",
            5,
            [0, 1, 2, 3],
            (0, 0),
            (256, 256),
            (128, 128),
            [36, 36, 16, 43],
            (36, 36, 16),
        ),
    ],
)
def test_get_slide_region_dedicated_channel(
    client,
    slide_id,
    level,
    channels,
    start_point,
    size,
    pixel_location,
    testpixel_multichannel,
    testpixel_rgb,
    image_format,
    image_quality,
    **kwargs,
):
    setup_mock(kwargs)
    str_channels = "&".join([f"image_channels={str(ch)}" for ch in channels])
    response = client.get(
        f"/v1/slides/{slide_id}/region/level/{level}/start/{start_point[0]}/{start_point[1]}/size/{size[0]}/{size[1]}?image_format={image_format}&image_quality={image_quality}&{str_channels}",
        stream=True,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == f"image/{image_format}"
    if response.headers["content-type"] == "image/tiff":
        image = get_tiff_image(response)
        x, y = image.pages.keyframe.imagewidth, image.pages.keyframe.imagelength
        assert (x == size[0]) or (y == size[1])
        narray = image.asarray()
        for i, value in enumerate(testpixel_multichannel):
            c = narray[i][pixel_location[0]][pixel_location[1]]
            assert c == value
    else:
        image = get_image(response)
        x, y = image.size
        assert (x == size[0]) or (y == size[1])
        if image_format in ["png", "bmp"]:
            assert image.getpixel((pixel_location[0], pixel_location[1])) == testpixel_rgb


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "slide_id, channels, expected_response",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", [2], 200),
        ("4b0ec5e0ec5e5e05ae9e500857314f20", [4], 400),
        ("46061cfc30a65acab7a1ed644771a340", [0], 200),
        ("46061cfc30a65acab7a1ed644771a340", [0, 1, 2], 200),
        ("46061cfc30a65acab7a1ed644771a340", [0, 1, 6], 400),
        ("46061cfc30a65acab7a1ed644771a340", [5], 400),
        ("46061cfc30a65acab7a1ed644771a340", [], 200),
        ("56ed11a2a9e95f87a1e466cf720ceffa", [0, 1, 2, 3, 4], 200),
        ("56ed11a2a9e95f87a1e466cf720ceffa", [4], 200),
        ("56ed11a2a9e95f87a1e466cf720ceffa", [5], 400),
    ],
)
def test_get_slide_region_invalid_channel(client, slide_id, channels, expected_response, **kwargs):
    setup_mock(kwargs)
    str_channels = "&".join([f"image_channels={str(ch)}" for ch in channels])
    response = client.get(
        f"/v1/slides/{slide_id}/region/level/2/start/0/0/size/64/64?{str_channels}",
        stream=True,
    )
    assert response.status_code == expected_response


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "slide_id, testpixel, start_x, start_y, size",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", (223, 217, 222), 15000, 15000, 30045),
        ("f863c2ef155654b1af0387acc7ebdb60", (223, 217, 222), 15000, 15000, 30045),
        ("c801ce3d1de45f2996e6a07b2d449bca", (218, 217, 225), 15000, 15000, 30045),
        ("7304006194f8530b9e19df1310a3670f", (221, 170, 219), 50000, 90000, 30045),
        ("cdad4692405c556ca63185bee512e95e", (0, 0, 0), 30000, 30000, 30045),
    ],
)
def test_get_slide_region_invalid(client, slide_id, testpixel, start_x, start_y, size, **kwargs):
    setup_mock(kwargs)
    level = 0
    size_x = size
    size_y = size + 198
    response = client.get(
        f"/v1/slides/{slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}", stream=True
    )
    assert response.status_code == 403


import timeit


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "slide_id,  tile_x, tile_y, level",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", 1, 1, 9),
        ("f863c2ef155654b1af0387acc7ebdb60", 1, 1, 2),
        ("c801ce3d1de45f2996e6a07b2d449bca", 1, 1, 12),
        ("7304006194f8530b9e19df1310a3670f", 1, 1, 9),
        ("46061cfc30a65acab7a1ed644771a340", 1, 1, 2),
        ("cdad4692405c556ca63185bee512e95e", 1, 1, 5),
        ("c4682788c7e85d739ce043b3f6eaff70", 1, 1, 4),
    ],
)
def test_get_slide_tile_timing(client, slide_id, tile_x, tile_y, level, **kwargs):
    setup_mock(kwargs)
    tic = timeit.default_timer()
    response = client.get(f"/v1/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}", stream=True)
    assert response.status_code == 200
    get_image(response)
    toc = timeit.default_timer()
    assert toc - tic < 2


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize(
    "image_format, image_quality",
    [("jpeg", 90), ("jpeg", 95), ("png", 0), ("png", 1), ("bmp", 0), ("gif", 0), ("tiff", 100)],
)
@pytest.mark.parametrize(
    "slide_id, testpixel, tile_x, tile_y, tile_size",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", (243, 243, 243), 21, 22, (128, 128)),
        ("f863c2ef155654b1af0387acc7ebdb60", (246, 246, 243), 21, 22, (256, 256)),
        ("c801ce3d1de45f2996e6a07b2d449bca", (121, 127, 123), 21, 22, (4096, 8)),
        ("7304006194f8530b9e19df1310a3670f", (255, 255, 255), 60, 60, (256, 256)),
        ("56ed11a2a9e95f87a1e466cf720ceffa", (30, 7, 6), 21, 22, (512, 512)),
        ("cdad4692405c556ca63185bee512e95e", (238, 238, 236), 210, 210, (256, 256)),
        ("c4682788c7e85d739ce043b3f6eaff70", (137, 75, 138), 210, 210, (256, 256)),
    ],
)
def test_get_slide_tile_valid(
    client, image_format, image_quality, slide_id, testpixel, tile_x, tile_y, tile_size, **kwargs
):
    setup_mock(kwargs)
    level = 0
    response = client.get(
        f"/v1/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}?image_format={image_format}&image_quality={image_quality}",
        stream=True,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == f"image/{image_format}"
    if response.headers["content-type"] == "image/tiff":
        image = get_tiff_image(response)
        x, y = image.pages.keyframe.imagewidth, image.pages.keyframe.imagelength
        assert (x == tile_size[0]) or (y == tile_size[1])
        narray = image.asarray()
        for i, value in enumerate(testpixel):
            c = narray[i][0][0]
            assert c == value
    else:
        image = get_image(response)
        x, y = image.size
        assert (x == tile_size[0]) or (y == tile_size[1])
        if image_format in ["png", "bmp"]:
            assert image.getpixel((0, 0)) == testpixel


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize("slide_id", ["4b0ec5e0ec5e5e05ae9e500857314f20"])
@pytest.mark.parametrize(
    "tile_x, level, expected_response",
    [
        (10, 1, 200),  # ok
        (10, 0, 200),  # ok
        (10, -1, 422),  # level -1 fails
        (10, 9, 200),  # level 10 ist coarsest level
        (10, 16, 422),  # level fails
    ],
)
def test_get_slide_tile_invalid(client, slide_id, tile_x, level, expected_response, **kwargs):
    setup_mock(kwargs)
    response = client.get(f"/v1/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_x}", stream=True)
    assert response.status_code == expected_response


@requests_mock.Mocker(real_http=True, kw="requests_mock")
@pytest.mark.parametrize("tile_size", [-1, 0, 1, 2500, 2501, 5000, 10000])
def test_get_region_maximum_extent(client, tile_size, **kwargs):
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
