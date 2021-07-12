import pytest

from wsi_service.tests.integration.plugin_example_tests.plugin_example_tests import (
    check_get_slide_info_valid,
    check_get_slide_label_valid,
    check_get_slide_macro_valid,
    check_get_slide_region_dedicated_channel,
    check_get_slide_region_invalid,
    check_get_slide_region_invalid_channel,
    check_get_slide_region_valid_brightfield,
    check_get_slide_thumbnail_valid,
    check_get_slide_tile_valid,
)


@pytest.mark.parametrize(
    "slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y",
    [
        (
            # TIFF
            "4b0ec5e0ec5e5e05ae9e500857314f20",
            3,
            8,
            10,
            50,
            (128, 128),
            46000,
            32914,
        ),
        (
            # SVS
            "f863c2ef155654b1af0387acc7ebdb60",
            3,
            8,
            3,
            499,
            (256, 256),
            46000,
            32914,
        ),
        (
            # NDPI
            "c801ce3d1de45f2996e6a07b2d449bca",
            3,
            8,
            13,
            227,
            (256, 256),
            122880,
            110592,
        ),
        (
            # MRXS
            "7304006194f8530b9e19df1310a3670f",
            3,
            8,
            10,
            234,
            (256, 256),
            101832,
            219976,
        ),
        (
            # BIF
            "cdad4692405c556ca63185bee512e95e",
            3,
            8,
            10,
            232,
            (256, 256),
            114943,
            76349,
        ),
        (
            # SCN
            "c4682788c7e85d739ce043b3f6eaff70",
            3,
            8,
            6,
            250,
            (256, 256),
            106259,
            306939,
        ),
    ],
)
def test_get_slide_info_valid(slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y):
    check_get_slide_info_valid(slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y)


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, return_value, pixel_location, testpixel_rgb, testpixel_multichannel",
    [
        (
            "4b0ec5e0ec5e5e05ae9e500857314f20",
            200,
            (5, 5),
            (245, 246, 246),
            (245, 246, 246),
        ),
        (
            "f863c2ef155654b1af0387acc7ebdb60",
            200,
            (5, 5),
            (243, 245, 244),
            (243, 245, 244),
        ),
        (
            "c801ce3d1de45f2996e6a07b2d449bca",
            200,
            (5, 5),
            (210, 200, 219),
            (210, 200, 219),
        ),
        (
            "7304006194f8530b9e19df1310a3670f",
            200,
            (5, 5),
            (225, 156, 216),
            (225, 156, 216),
        ),
        (
            "cdad4692405c556ca63185bee512e95e",
            200,
            (5, 5),
            (242, 242, 242),
            (242, 242, 242),
        ),
        (
            "c4682788c7e85d739ce043b3f6eaff70",
            200,
            (5, 5),
            (217, 206, 213),
            (217, 206, 213),
        ),
    ],
)
def test_get_slide_thumbnail_valid(
    image_format,
    image_quality,
    slide_id,
    return_value,
    pixel_location,
    testpixel_rgb,
    testpixel_multichannel,
):
    check_get_slide_thumbnail_valid(
        image_format,
        image_quality,
        slide_id,
        return_value,
        pixel_location,
        testpixel_rgb,
        testpixel_multichannel,
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, has_label, pixel_location, testpixel",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", False, (), ()),
        ("f863c2ef155654b1af0387acc7ebdb60", True, (0, 0), (0, 0, 0)),
        ("f863c2ef155654b1af0387acc7ebdb60", True, (50, 50), (202, 131, 50)),
        ("c801ce3d1de45f2996e6a07b2d449bca", False, (), ()),
        ("7304006194f8530b9e19df1310a3670f", True, (0, 0), (19, 19, 19)),
        ("7304006194f8530b9e19df1310a3670f", True, (50, 50), (23, 23, 23)),
        ("cdad4692405c556ca63185bee512e95e", False, (), ()),
        ("c4682788c7e85d739ce043b3f6eaff70", False, (), ()),
    ],
)
def test_get_slide_label_valid(image_format, image_quality, slide_id, has_label, pixel_location, testpixel):
    check_get_slide_label_valid(image_format, image_quality, slide_id, has_label, pixel_location, testpixel)


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, return_value, pixel_location, testpixel",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", 404, (), ()),
        ("f863c2ef155654b1af0387acc7ebdb60", 200, (0, 0), (0, 0, 0)),
        ("f863c2ef155654b1af0387acc7ebdb60", 200, (50, 50), (238, 240, 240)),
        ("c801ce3d1de45f2996e6a07b2d449bca", 200, (0, 0), (117, 117, 117)),
        ("c801ce3d1de45f2996e6a07b2d449bca", 200, (50, 50), (12, 12, 12)),
        ("7304006194f8530b9e19df1310a3670f", 200, (0, 0), (221, 221, 221)),
        ("7304006194f8530b9e19df1310a3670f", 200, (50, 50), (157, 157, 157)),
        ("cdad4692405c556ca63185bee512e95e", 200, (0, 0), (95, 76, 51)),
        ("c4682788c7e85d739ce043b3f6eaff70", 200, (0, 0), (2, 2, 2)),
    ],
)
def test_get_slide_macro_valid(image_format, image_quality, slide_id, return_value, pixel_location, testpixel):
    check_get_slide_macro_valid(image_format, image_quality, slide_id, return_value, pixel_location, testpixel)


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 100), ("png", 100), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id,  pixel_location, testpixel, start_x, start_y, size",
    [
        (
            "4b0ec5e0ec5e5e05ae9e500857314f20",
            (0, 0),
            (255, 236, 253),
            15000,
            15000,
            345,
        ),
        (
            "f863c2ef155654b1af0387acc7ebdb60",
            (0, 0),
            (255, 235, 255),
            15000,
            15000,
            345,
        ),
        (
            "c801ce3d1de45f2996e6a07b2d449bca",
            (0, 0),
            (220, 219, 227),
            15000,
            15000,
            345,
        ),
        (
            "7304006194f8530b9e19df1310a3670f",
            (0, 0),
            (231, 182, 212),
            50000,
            90000,
            345,
        ),
        (
            "cdad4692405c556ca63185bee512e95e",
            (0, 0),
            (245, 241, 242),
            30000,
            30000,
            345,
        ),
        ("c4682788c7e85d739ce043b3f6eaff70", (0, 0), (131, 59, 122), 50000, 55000, 345),
    ],
)
def test_get_slide_region_valid_brightfield(
    image_format,
    image_quality,
    slide_id,
    pixel_location,
    testpixel,
    start_x,
    start_y,
    size,
):
    check_get_slide_region_valid_brightfield(
        image_format,
        image_quality,
        slide_id,
        pixel_location,
        testpixel,
        start_x,
        start_y,
        size,
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, testpixel, tile_x, tile_y, tile_size",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", (243, 243, 243), 21, 22, (128, 128)),
        ("f863c2ef155654b1af0387acc7ebdb60", (246, 246, 243), 21, 22, (256, 256)),
        ("c801ce3d1de45f2996e6a07b2d449bca", (222, 221, 229), 21, 22, (256, 256)),
        ("7304006194f8530b9e19df1310a3670f", (255, 255, 255), 60, 60, (256, 256)),
        ("cdad4692405c556ca63185bee512e95e", (238, 238, 236), 210, 210, (256, 256)),
        ("c4682788c7e85d739ce043b3f6eaff70", (137, 75, 138), 210, 210, (256, 256)),
    ],
)
def test_get_slide_tile_valid(image_format, image_quality, slide_id, testpixel, tile_x, tile_y, tile_size):
    check_get_slide_tile_valid(image_format, image_quality, slide_id, testpixel, tile_x, tile_y, tile_size)


@pytest.mark.parametrize(
    "slide_id, testpixel, start_x, start_y, size",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", (223, 217, 222), 15000, 15000, 30045),
    ],
)
def test_get_slide_region_invalid(slide_id, testpixel, start_x, start_y, size):
    check_get_slide_region_invalid(slide_id, testpixel, start_x, start_y, size)


@pytest.mark.parametrize("image_format, image_quality", [("png", 100), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, level, channels, start_point, size, pixel_location, testpixel_multichannel, testpixel_rgb",
    [
        (
            "4b0ec5e0ec5e5e05ae9e500857314f20",
            7,
            [0],
            (0, 0),
            (256, 256),
            (128, 128),
            [246],
            (246, 0, 0),
        ),
    ],
)
def test_get_slide_region_dedicated_channel(
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
):
    check_get_slide_region_dedicated_channel(
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
    )


@pytest.mark.parametrize(
    "slide_id, channels, expected_response",
    [
        ("4b0ec5e0ec5e5e05ae9e500857314f20", [2], 200),
        ("4b0ec5e0ec5e5e05ae9e500857314f20", [4], 400),
    ],
)
def test_get_slide_region_invalid_channel(slide_id, channels, expected_response):
    check_get_slide_region_invalid_channel(slide_id, channels, expected_response)
