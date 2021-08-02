import pytest

from wsi_service.tests.integration.plugin_example_tests.plugin_example_tests import (
    check_get_slide_info_valid,
)


@pytest.mark.parametrize(
    "slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y",
    [
        # JPG
        ("5f858519fc285ce78161b023746df590", 3, 8, 1, 0, (500, 358), 500, 358),
        # PNG
        ("0f72fba3dc2359e18c09a1d59cd62ed0", 3, 8, 1, 0, (500, 358), 500, 358),
    ],
)
def test_get_slide_info_valid(
    slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y
):
    check_get_slide_info_valid(
        slide_id, channels, channel_depth, num_levels, pixel_size_nm, tile_size, x, y
    )
