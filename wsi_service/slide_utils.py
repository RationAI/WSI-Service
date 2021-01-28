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
                extent=Extent(
                    x=level_dimensions[level][0],
                    y=level_dimensions[level][1],
                    z=1,
                ),
                downsample_factor=level_downsamples[level],
                generated=False,
            ),
        )
    return levels


def get_generated_levels(level_dimensions, coarsest_native_level):
    levels = []
    for level in range(calc_num_levels(level_dimensions)):
        extent = Extent(
            x=level_dimensions[0] / (2 ** level),
            y=level_dimensions[1] / (2 ** level),
            z=1,
        )
        downsample_factor = 2 ** level
        if (
            downsample_factor > 4 * coarsest_native_level.downsample_factor
        ):  # only include levels up to two levels below coarsest native level
            continue
        levels.append(
            Level(
                extent=extent,
                downsample_factor=downsample_factor,
                generated=True,
            )
        )
    return levels


def check_generated_levels_for_originals(original_levels, generated_levels):
    for generated_level in generated_levels:
        for original_level in original_levels:
            if (
                original_level.extent.x == generated_level.extent.x
                and original_level.extent.y == generated_level.extent.y
            ):
                generated_level.generated = False
    return generated_level
