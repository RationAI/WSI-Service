import pytest

from wsi_service.tests.integration.plugin_example_tests.plugin_example_tests import (
    check_get_slide_info_valid,
    check_get_slide_label_valid,
    check_get_slide_macro_valid,
    check_get_slide_region_dedicated_channel,
    check_get_slide_region_invalid_channel,
    check_get_slide_region_valid_fluorescence,
    check_get_slide_thumbnail_valid,
    check_get_slide_tile_valid,
)


@pytest.mark.parametrize(
    "slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y",
    [
        # OME-TIFF 3x16bit
        ("80f38182247757799ad732bf6d035ac0", 3, 16, 3, 325, (256, 256), 11260, 22300),
        # OME-TIFF 5x8bit
        ("37b5c722d1425395b1817474dd41b946", 5, 8, 6, 498, (512, 512), 24960, 34560),
    ],
)
def test_get_slide_info_valid(slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y):
    check_get_slide_info_valid(slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y)


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, return_value, pixel_location, testpixel_rgb, testpixel_multichannel",
    [
        ("80f38182247757799ad732bf6d035ac0", 200, (0, 0), (0, 0, 0), (3, 2, 0)),
        (
            "80f38182247757799ad732bf6d035ac0",
            200,
            (10, 10),
            (10, 6, 1),
            (675, 432, 121),
        ),
        ("37b5c722d1425395b1817474dd41b946", 200, (0, 0), (0, 0, 0), (0, 0, 0)),
        (
            "37b5c722d1425395b1817474dd41b946",
            200,
            (10, 10),
            (87, 51, 23),
            (5654, 3341, 1542),
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
        ("80f38182247757799ad732bf6d035ac0", False, (), ()),
        ("37b5c722d1425395b1817474dd41b946", False, (), ()),
    ],
)
def test_get_slide_label_valid(image_format, image_quality, slide_id, has_label, pixel_location, testpixel):
    check_get_slide_label_valid(image_format, image_quality, slide_id, has_label, pixel_location, testpixel)


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, return_value, pixel_location, testpixel",
    [
        ("80f38182247757799ad732bf6d035ac0", 404, (), ()),
        ("37b5c722d1425395b1817474dd41b946", 404, (), ()),
    ],
)
def test_get_slide_macro_valid(image_format, image_quality, slide_id, return_value, pixel_location, testpixel):
    check_get_slide_macro_valid(image_format, image_quality, slide_id, return_value, pixel_location, testpixel)


@pytest.mark.parametrize("image_format, image_quality", [("tiff", 100), ("jpeg", 90), ("png", 100)])
@pytest.mark.parametrize(
    "slide_id, channels, start_point, size, pixel_location, testpixel_multichannel, testpixel_rgb",
    [
        (
            "80f38182247757799ad732bf6d035ac0",
            3,
            (0, 0),
            (256, 256),
            (0, 0),
            (0, 0, 0),
            (0, 0, 0),
        ),
        (
            "80f38182247757799ad732bf6d035ac0",
            3,
            (512, 512),
            (256, 256),
            (100, 100),
            (3900, 2792, 3859),
            (60, 43, 60),
        ),
        (
            "37b5c722d1425395b1817474dd41b946",
            5,
            (0, 0),
            (256, 256),
            (0, 0),
            (0, 0, 0),
            (0, 0, 0),
        ),
        (
            "37b5c722d1425395b1817474dd41b946",
            5,
            (512, 512),
            (256, 256),
            (200, 200),
            (4, 0, 0),
            (4, 0, 0),
        ),
    ],
)
def test_get_slide_region_valid_fluorescence(
    slide_id,
    channels,
    start_point,
    size,
    pixel_location,
    testpixel_multichannel,
    testpixel_rgb,
    image_format,
    image_quality,
):
    check_get_slide_region_valid_fluorescence(
        slide_id,
        channels,
        start_point,
        size,
        pixel_location,
        testpixel_multichannel,
        testpixel_rgb,
        image_format,
        image_quality,
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, testpixel, tile_x, tile_y, tile_size",
    [("37b5c722d1425395b1817474dd41b946", (30, 7, 6), 21, 22, (512, 512))],
)
def test_get_slide_tile_valid(image_format, image_quality, slide_id, testpixel, tile_x, tile_y, tile_size):
    check_get_slide_tile_valid(image_format, image_quality, slide_id, testpixel, tile_x, tile_y, tile_size)


@pytest.mark.parametrize("image_format, image_quality", [("png", 100), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, level, channels, start_point, size, pixel_location, testpixel_multichannel, testpixel_rgb",
    [
        (
            "80f38182247757799ad732bf6d035ac0",
            2,
            [0],
            (0, 0),
            (256, 256),
            (128, 128),
            [740],
            13,
        ),
        (
            "80f38182247757799ad732bf6d035ac0",
            2,
            [0, 1],
            (0, 0),
            (256, 256),
            (128, 128),
            [740, 525],
            (13, 9, 0),
        ),
        (
            "37b5c722d1425395b1817474dd41b946",
            5,
            [0],
            (0, 0),
            (256, 256),
            (128, 128),
            [36],
            36,
        ),
        (
            "37b5c722d1425395b1817474dd41b946",
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
        ("80f38182247757799ad732bf6d035ac0", [0], 200),
        ("80f38182247757799ad732bf6d035ac0", [0, 1, 2], 200),
        ("80f38182247757799ad732bf6d035ac0", [0, 1, 6], 400),
        ("80f38182247757799ad732bf6d035ac0", [5], 400),
        ("80f38182247757799ad732bf6d035ac0", [], 200),
        ("37b5c722d1425395b1817474dd41b946", [0, 1, 2, 3, 4], 200),
        ("37b5c722d1425395b1817474dd41b946", [4], 200),
        ("37b5c722d1425395b1817474dd41b946", [5], 400),
    ],
)
def test_get_slide_region_invalid_channel(slide_id, channels, expected_response):
    check_get_slide_region_invalid_channel(slide_id, channels, expected_response)
