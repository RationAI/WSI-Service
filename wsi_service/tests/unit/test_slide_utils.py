from wsi_service.utils.slide_utils import get_original_levels, get_rgb_channel_list


def test_get_original_levels():
    level_count = 2
    level_dimensions = [[64, 64], [32, 32]]
    level_downsamples = [1, 2]
    levels = get_original_levels(level_count, level_dimensions, level_downsamples)
    assert len(levels) == level_count
    assert levels[0].downsample_factor == level_downsamples[0]
    assert levels[1].downsample_factor == level_downsamples[1]
    assert levels[0].extent.x == level_dimensions[0][0]
    assert levels[0].extent.y == level_dimensions[0][1]
    assert levels[1].extent.x == level_dimensions[1][0]
    assert levels[1].extent.y == level_dimensions[1][1]


def test_get_rgb_channel_list():
    channels = get_rgb_channel_list()
    names = ["Red", "Green", "Blue"]
    rgba = [[255, 0, 0, 0], [0, 255, 0, 0], [0, 0, 255, 0]]
    assert len(channels) == 3
    for i in range(3):
        assert channels[i].id == i
        assert channels[i].name == names[i]
        assert channels[i].color.r == rgba[i][0]
        assert channels[i].color.g == rgba[i][1]
        assert channels[i].color.b == rgba[i][2]
        assert channels[i].color.a == rgba[i][3]
