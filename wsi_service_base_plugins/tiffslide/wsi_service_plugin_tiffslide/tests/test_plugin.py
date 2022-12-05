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
            "f5f3a03b77fb5e0497b95eaff84e9a21",
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
            "8d32dba05a4558218880f06caf30d3ac",
            3,
            8,
            3,
            499,
            (256, 256),
            46000,
            32914,
        ),
    ],
)
def test_get_slide_info_valid(slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y):
    check_get_slide_info_valid(
        slide_id,
        channels,
        channel_depth,
        num_levels,
        pixel_size_nm,
        tile_size,
        x,
        y,
        plugin="tiffslide",
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, return_value, pixel_location, testpixel_rgb, testpixel_multichannel",
    [
        (
            "f5f3a03b77fb5e0497b95eaff84e9a21",
            200,
            (5, 5),
            (245, 246, 246),
            (245, 246, 246),
        ),
        (
            "8d32dba05a4558218880f06caf30d3ac",
            200,
            (5, 5),
            (244, 246, 245),
            (244, 246, 245),
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
        plugin="tiffslide",
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, has_label, pixel_location, testpixel",
    [
        ("f5f3a03b77fb5e0497b95eaff84e9a21", False, (), ()),
        ("8d32dba05a4558218880f06caf30d3ac", True, (0, 0), (0, 0, 0)),
        ("8d32dba05a4558218880f06caf30d3ac", True, (50, 50), (202, 131, 50)),
    ],
)
def test_get_slide_label_valid(image_format, image_quality, slide_id, has_label, pixel_location, testpixel):
    check_get_slide_label_valid(
        image_format,
        image_quality,
        slide_id,
        has_label,
        pixel_location,
        testpixel,
        plugin="tiffslide",
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, return_value, pixel_location, testpixel",
    [
        ("f5f3a03b77fb5e0497b95eaff84e9a21", 404, (), ()),
        ("8d32dba05a4558218880f06caf30d3ac", 200, (0, 0), (0, 0, 0)),
        ("8d32dba05a4558218880f06caf30d3ac", 200, (50, 50), (238, 240, 240)),
    ],
)
def test_get_slide_macro_valid(image_format, image_quality, slide_id, return_value, pixel_location, testpixel):
    check_get_slide_macro_valid(
        image_format,
        image_quality,
        slide_id,
        return_value,
        pixel_location,
        testpixel,
        plugin="tiffslide",
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 100), ("png", 100), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id,  pixel_location, testpixel, start_x, start_y, size",
    [
        (
            "f5f3a03b77fb5e0497b95eaff84e9a21",
            (0, 0),
            (255, 236, 253),
            15000,
            15000,
            345,
        ),
        (
            "8d32dba05a4558218880f06caf30d3ac",
            (0, 0),
            (255, 235, 255),
            15000,
            15000,
            345,
        ),
        (
            "f5f3a03b77fb5e0497b95eaff84e9a21",
            (0, 0),
            (255, 255, 255),
            -1_000_000,
            -1_000_000,
            1,
        ),
        (
            "f5f3a03b77fb5e0497b95eaff84e9a21",
            (0, 0),
            (255, 255, 255),
            1_000_000,
            1_000_000,
            1,
        ),
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
        plugin="tiffslide",
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, testpixel, tile_x, tile_y, tile_size",
    [
        ("f5f3a03b77fb5e0497b95eaff84e9a21", (243, 243, 243), 21, 22, (128, 128)),
        ("8d32dba05a4558218880f06caf30d3ac", (246, 246, 243), 21, 22, (256, 256)),
        (
            "f5f3a03b77fb5e0497b95eaff84e9a21",
            (255, 255, 255),
            -1_000_000,
            -1_000_000,
            (128, 128),
        ),
        (
            "f5f3a03b77fb5e0497b95eaff84e9a21",
            (255, 255, 255),
            1_000_000,
            1_000_000,
            (128, 128),
        ),
    ],
)
def test_get_slide_tile_valid(image_format, image_quality, slide_id, testpixel, tile_x, tile_y, tile_size):
    check_get_slide_tile_valid(
        image_format,
        image_quality,
        slide_id,
        testpixel,
        tile_x,
        tile_y,
        tile_size,
        plugin="tiffslide",
    )


@pytest.mark.parametrize(
    "slide_id, testpixel, start_x, start_y, size, status_code",
    [("f5f3a03b77fb5e0497b95eaff84e9a21", (223, 217, 222), 15000, 15000, 30045, 422)],
)
def test_get_slide_region_invalid(slide_id, testpixel, start_x, start_y, size, status_code):
    check_get_slide_region_invalid(slide_id, testpixel, start_x, start_y, size, status_code, plugin="tiffslide")


@pytest.mark.parametrize("image_format, image_quality", [("png", 100), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, level, channels, start_point, size, pixel_location, testpixel_multichannel, testpixel_rgb",
    [
        (
            "f5f3a03b77fb5e0497b95eaff84e9a21",
            7,
            [0],
            (0, 0),
            (256, 256),
            (128, 128),
            [246],
            (246, 0, 0),
        )
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
        plugin="tiffslide",
    )


@pytest.mark.parametrize(
    "slide_id, channels, expected_response",
    [
        ("f5f3a03b77fb5e0497b95eaff84e9a21", [2], 200),
        ("f5f3a03b77fb5e0497b95eaff84e9a21", [4], 400),
    ],
)
def test_get_slide_region_invalid_channel(slide_id, channels, expected_response):
    check_get_slide_region_invalid_channel(slide_id, channels, expected_response, plugin="tiffslide")
