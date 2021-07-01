import math

from wsi_service.models.slide import SlideChannel, SlideColor, SlideExtent, SlideLevel


def get_original_levels(level_count, level_dimensions, level_downsamples):
    levels = []
    for level in range(level_count):
        levels.append(
            SlideLevel(
                extent=SlideExtent(x=level_dimensions[level][0], y=level_dimensions[level][1], z=1),
                downsample_factor=level_downsamples[level],
            )
        )
    return levels


def get_rgb_channel_list():
    channels = []
    channels.append(SlideChannel(id=0, name="Red", color=SlideColor(r=255, g=0, b=0, a=0)))
    channels.append(SlideChannel(id=1, name="Green", color=SlideColor(r=0, g=255, b=0, a=0)))
    channels.append(SlideChannel(id=2, name="Blue", color=SlideColor(r=0, g=0, b=255, a=0)))
    return channels
