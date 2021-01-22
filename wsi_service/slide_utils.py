import math

import openslide
import PIL
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


def get_levels_openslide(openslide_slide):
    original_levels = get_original_levels(
        openslide_slide.level_count, openslide_slide.level_dimensions, openslide_slide.level_downsamples
    )
    generated_levels = get_generated_levels(openslide_slide.dimensions, original_levels[-1])
    check_generated_levels_for_originals(original_levels, generated_levels)
    return generated_levels


def get_pixel_size(openslide_slide):
    if openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] == "generic-tiff":
        if openslide_slide.properties["tiff.ResolutionUnit"] == "centimeter":
            pixel_per_cm_x = float(openslide_slide.properties["tiff.XResolution"])
            pixel_per_cm_y = float(openslide_slide.properties["tiff.YResolution"])
            pixel_size_nm_x = 1e8 / pixel_per_cm_x
            pixel_size_nm_y = 1e8 / pixel_per_cm_y
        else:
            raise ("Unable to extract pixel size from metadata.")
    elif (
        openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] == "aperio"
        or openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] == "mirax"
        or openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] == "hamamatsu"
    ):
        pixel_size_nm_x = 1000.0 * float(openslide_slide.properties[openslide.PROPERTY_NAME_MPP_X])
        pixel_size_nm_y = 1000.0 * float(openslide_slide.properties[openslide.PROPERTY_NAME_MPP_Y])
    else:
        raise ("Unable to extract pixel size from metadata.")
    return PixelSizeNm(x=pixel_size_nm_x, y=pixel_size_nm_y)


def get_tile_extent(openslide_slide):
    if (
        "openslide.level[0].tile-height" in openslide_slide.properties
        and "openslide.level[0].tile-width" in openslide_slide.properties
    ):
        tile_height = openslide_slide.properties["openslide.level[0].tile-height"]
        tile_width = openslide_slide.properties["openslide.level[0].tile-width"]
    else:
        tile_height = 256
        tile_width = 256
    return Extent(x=tile_width, y=tile_height, z=1)


def get_slide_info_openslide(openslide_slide, slide_id):
    try:
        levels = get_levels_openslide(openslide_slide)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to retrieve slide level data. [{e}]",
        )
    try:
        slide_info = SlideInfo(
            id=slide_id,
            channel_count=4,  # rgba
            channel_depth=8,  # 8bit each channel
            extent=Extent(x=openslide_slide.dimensions[0], y=openslide_slide.dimensions[1], z=1),
            pixel_size_nm=get_pixel_size(openslide_slide),
            tile_extent=get_tile_extent(openslide_slide),
            num_levels=len(levels),
            levels=levels,
        )
        return slide_info
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to gather slide infos. [{e}]",
        )


def get_levels_ome_tif(tif_slide):
    levels = tif_slide.series[0].levels
    level_count = len(levels)
    level_dimensions = []
    level_downsamples = []

    for i, item in enumerate(levels):
        level_dimensions.append([item.keyframe.imagewidth, item.keyframe.imagelength])
        if i > 0:
            level_downsamples.append(level_dimensions[i - 1][0] / item.keyframe.imagewidth)
        else:
            level_downsamples.append(1)

    original_levels = get_original_levels(level_count, level_dimensions, level_downsamples)
    generated_levels = get_generated_levels(level_dimensions[0], original_levels[-1])
    check_generated_levels_for_originals(original_levels, generated_levels)
    return generated_levels


def get_slide_info_ome_tif(tif_slide, slide_id, pixel_size):
    serie = tif_slide.series[0]
    levels = get_levels_ome_tif(tif_slide)

    try:
        slide_info = SlideInfo(
            id=slide_id,
            channel_count=len(serie.levels[0].pages),
            channel_depth=serie.keyframe.bitspersample,
            extent=Extent(x=serie.keyframe.imagewidth, y=serie.keyframe.imagedepth, z=serie.keyframe.imagedepth),
            pixel_size_nm=pixel_size,
            tile_extent=Extent(x=serie.keyframe.tilewidth, y=serie.keyframe.tilelength, z=serie.keyframe.tiledepth),
            num_levels=len(levels),
            levels=levels,
        )
        return slide_info
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to gather slide infos. [{e}]",
        )


def rgba_to_rgb_with_background_color(image_rgba, background_color=(255, 255, 255)):
    image_rgb = PIL.Image.new("RGB", image_rgba.size, background_color)
    image_rgb.paste(image_rgba, mask=image_rgba.split()[3])
    return image_rgb
