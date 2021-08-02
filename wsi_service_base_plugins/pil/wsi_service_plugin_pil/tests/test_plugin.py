import pytest

from wsi_service.tests.integration.plugin_example_tests.plugin_example_tests import (
    check_get_slide_info_valid,
    check_get_slide_region_valid_brightfield,
    check_get_slide_thumbnail_valid,
    check_get_slide_tile_valid,
)


@pytest.mark.parametrize(
    "slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y",
    [
        # JPG
        ("5f858519fc285ce78161b023746df590", 3, 8, 1, -1, (500, 358), 500, 358),
        # PNG
        ("0f72fba3dc2359e18c09a1d59cd62ed0", 3, 8, 1, -1, (500, 358), 500, 358),
    ],
)
def test_get_slide_info_valid(slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y):
    check_get_slide_info_valid(slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y)


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90)])
@pytest.mark.parametrize(
    "slide_id, return_value, pixel_location, testpixel_rgb",
    [
        (
            "5f858519fc285ce78161b023746df590",
            200,
            (5, 5),
            (245, 246, 246),
        ),
        (
            "0f72fba3dc2359e18c09a1d59cd62ed0",
            200,
            (5, 5),
            (243, 245, 244),
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
):
    check_get_slide_thumbnail_valid(
        image_format,
        image_quality,
        slide_id,
        return_value,
        pixel_location,
        testpixel_rgb,
        (None, None, None),
    )


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90)])
@pytest.mark.parametrize(
    "slide_id, testpixel, tile_x, tile_y, tile_size",
    [
        ("5f858519fc285ce78161b023746df590", (243, 243, 243), 0, 0, (500, 358)),
        ("0f72fba3dc2359e18c09a1d59cd62ed0", (243, 243, 243), 0, 0, (500, 358)),
    ],
)
def test_get_slide_tile_valid(image_format, image_quality, slide_id, testpixel, tile_x, tile_y, tile_size):
    check_get_slide_tile_valid(image_format, image_quality, slide_id, testpixel, tile_x, tile_y, tile_size)


@pytest.mark.parametrize("image_format, image_quality", [("jpeg", 90)])
@pytest.mark.parametrize(
    "slide_id,  pixel_location, testpixel, start_x, start_y, size",
    [
        (
            "4b0ec5e0ec5e5e05ae9e500857314f20",
            (0, 0),
            (243, 243, 243),
            0,
            0,
            128,
        )
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
