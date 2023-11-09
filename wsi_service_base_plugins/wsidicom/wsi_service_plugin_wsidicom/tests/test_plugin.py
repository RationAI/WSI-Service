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
            # Aperio DICOM wsidicomizer
            "50f3010ed9a55f04b2e0d88cd19c6923",
            3,
            8,
            3,
            499,
            (256, 256),
            46000,
            32914,
        ),
        (
            # Mirax DICOM wsidicomizer
            "d3fc669ff08d57a4a409340d54d6bf4f",
            3,
            8,
            10,
            234,
            (512, 512),
            94794,
            179005,
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
        plugin="wsidicom",
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, return_value, pixel_location, testpixel_rgb, testpixel_multichannel",
    [
        (
            "50f3010ed9a55f04b2e0d88cd19c6923",
            200,
            (5, 5),
            (243, 245, 244),
            (243, 245, 244),
        ),
        (
            "d3fc669ff08d57a4a409340d54d6bf4f",
            200,
            (5, 5),
            (222, 146, 213),
            (222, 146, 213),
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
        plugin="wsidicom",
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, has_label, pixel_location, testpixel",
    [
        ("50f3010ed9a55f04b2e0d88cd19c6923", True, (0, 0), (0, 0, 0)),
        ("50f3010ed9a55f04b2e0d88cd19c6923", True, (50, 50), (53, 131, 195)),
        ("d3fc669ff08d57a4a409340d54d6bf4f", True, (0, 0), (19, 19, 19)),
        ("d3fc669ff08d57a4a409340d54d6bf4f", True, (50, 50), (23, 23, 23)),
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
        plugin="wsidicom",
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, return_value, pixel_location, testpixel",
    [
        ("50f3010ed9a55f04b2e0d88cd19c6923", 200, (0, 0), (0, 0, 0)),
        ("50f3010ed9a55f04b2e0d88cd19c6923", 200, (50, 50), (238, 240, 240)),
        ("d3fc669ff08d57a4a409340d54d6bf4f", 200, (0, 0), (220, 220, 220)),
        ("d3fc669ff08d57a4a409340d54d6bf4f", 200, (50, 50), (156, 156, 156)),
    ],
)
def test_get_slide_macro_valid(image_format, image_quality, slide_id, return_value, pixel_location, testpixel):
    print(f"Slide ID: {slide_id}")
    check_get_slide_macro_valid(
        image_format,
        image_quality,
        slide_id,
        return_value,
        pixel_location,
        testpixel,
        plugin="wsidicom",
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 100), ("png", 100), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id,  pixel_location, testpixel, start_x, start_y, size",
    [
        (
            "50f3010ed9a55f04b2e0d88cd19c6923",
            (0, 0),
            (255, 235, 255),
            15000,
            15000,
            345,
        ),
        (
            "d3fc669ff08d57a4a409340d54d6bf4f",
            (0, 0),
            (255, 253, 254),
            15000,
            15000,
            345,
        ),
        (
            "50f3010ed9a55f04b2e0d88cd19c6923",
            (0, 0),
            (255, 255, 255),
            -1_000_000,
            -1_000_000,
            1,
        ),
        (
            "50f3010ed9a55f04b2e0d88cd19c6923",
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
        plugin="wsidicom",
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90), ("png", 0), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, testpixel, tile_x, tile_y, tile_size",
    [
        ("50f3010ed9a55f04b2e0d88cd19c6923", (246, 246, 243), 21, 22, (256, 256)),
        ("d3fc669ff08d57a4a409340d54d6bf4f", (229, 163, 225), 60, 60, (512, 512)),
        (
            "50f3010ed9a55f04b2e0d88cd19c6923",
            (255, 255, 255),
            -1_000_000,
            -1_000_000,
            (256, 256),
        ),
        (
            "50f3010ed9a55f04b2e0d88cd19c6923",
            (255, 255, 255),
            1_000_000,
            1_000_000,
            (256, 256),
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
        plugin="wsidicom",
    )


@pytest.mark.parametrize(
    "slide_id, testpixel, start_x, start_y, size, status_code",
    [("50f3010ed9a55f04b2e0d88cd19c6923", (223, 217, 222), 15000, 15000, 30045, 422)],
)
def test_get_slide_region_invalid(slide_id, testpixel, start_x, start_y, size, status_code):
    check_get_slide_region_invalid(slide_id, testpixel, start_x, start_y, size, status_code, plugin="wsidicom")


@pytest.mark.parametrize("image_format, image_quality", [("png", 100), ("tiff", 100)])
@pytest.mark.parametrize(
    "slide_id, level, channels, start_point, size, pixel_location, testpixel_multichannel, testpixel_rgb",
    [
        (
            "d3fc669ff08d57a4a409340d54d6bf4f",
            7,
            [0],
            (0, 0),
            (256, 256),
            (128, 128),
            [249],
            (249, 0, 0),
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
        plugin="wsidicom",
    )


@pytest.mark.parametrize(
    "slide_id, channels, expected_response",
    [
        ("d3fc669ff08d57a4a409340d54d6bf4f", [2], 200),
        ("d3fc669ff08d57a4a409340d54d6bf4f", [4], 400),
    ],
)
def test_get_slide_region_invalid_channel(slide_id, channels, expected_response):
    check_get_slide_region_invalid_channel(slide_id, channels, expected_response, plugin="wsidicom")
