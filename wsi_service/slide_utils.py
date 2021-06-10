import math

from wsi_service.models.slide import Channel, Color, Extent, Level


def calc_num_levels(dimensions):
    min_extent = min(dimensions)
    return int(math.log2(min_extent) + 1)


def get_original_levels(level_count, level_dimensions, level_downsamples):
    levels = []
    for level in range(level_count):
        levels.append(
            Level(
                extent=Extent(x=level_dimensions[level][0], y=level_dimensions[level][1], z=1),
                downsample_factor=level_downsamples[level],
            )
        )
    return levels


def get_rgb_channel_list():
    channels = []
    channels.append(Channel(id=0, name="Red", color=Color(r=255, g=0, b=0, a=0)))
    channels.append(Channel(id=1, name="Green", color=Color(r=0, g=255, b=0, a=0)))
    channels.append(Channel(id=2, name="Blue", color=Color(r=0, g=0, b=255, a=0)))
    return channels
