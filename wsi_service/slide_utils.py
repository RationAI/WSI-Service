import math

from fastapi import HTTPException

from wsi_service.models.slide import Extent, Level, PixelSizeNm, SlideInfo


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
