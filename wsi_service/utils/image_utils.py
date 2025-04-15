from io import BytesIO

import numpy as np
from fastapi import HTTPException
from PIL import Image


def rgba_to_rgb_with_background_color(image_rgba, padding_color):
    if image_rgba.info.get("transparency", None) is not None or image_rgba.mode == "RGBA":
        image_rgb = Image.new("RGB", image_rgba.size, padding_color)
        image_rgb.paste(image_rgba, mask=image_rgba.split()[3])
    else:
        image_rgb = image_rgba.convert("RGB")
    return image_rgb


def convert_narray_uintX_to_uint8(array, exp=16, lower=None, upper=None):
    if exp not in [8, 16, 32, 64]:
        raise ValueError("Only exponent in range [8, 16, 32, 64] supported")
    if lower is not None and not (0 <= lower < 2**exp):
        raise ValueError(f"lower bound must be between 0 and 2**{exp}")
    if upper is not None and not (0 <= upper < 2**exp):
        raise ValueError(f"upper bound must be between 0 and 2**{exp}")
    if not lower and not upper and exp == 8:
        return array
    if lower is None:
        lower = 0
    if upper is None:
        upper = (2**exp) - 1
        # default upper bound for bitness > 8 to enhance contrast/brightness
        if exp > 8:
            upper = (2**exp) / (exp / 4)

    temp_array = np.divide((array - lower), (upper - lower))
    temp_array = np.clip(temp_array * 255, 0, 255)
    return temp_array.astype(np.uint8)


def convert_int_to_rgba_array(i):
    return [(i >> 24) & 0xFF, (i >> 16) & 0xFF, (i >> 8) & 0xFF, i & 0xFF]


def convert_rgba_array_to_int(rgba):
    return int.from_bytes(rgba, byteorder="big", signed=True)


def convert_rgb_image_for_channels(image_tile, image_channel):
    r = 1 if 0 in image_channel else 0
    g = 1 if 1 in image_channel else 0
    b = 1 if 2 in image_channel else 0
    conv_matrix = (r, 0, 0, 0, 0, g, 0, 0, 0, 0, b, 0)
    converted_image = image_tile.convert("RGB", conv_matrix)
    return converted_image


def convert_rgb_image_by_color(image_tile, rgba):
    conv_matrix = (rgba[0] / 255, 0, 0, 0, 0, rgba[1] / 255, 0, 0, 0, 0, rgba[2] / 255, 0)
    converted_image = image_tile.convert("RGB", conv_matrix)
    return converted_image


def convert_narray_to_pil_image(narray, lower=None, upper=None, mode="RGB"):
    if narray.dtype == np.uint8:
        narray_uint8 = narray
    elif narray.dtype == np.uint16:
        narray_uint8 = convert_narray_uintX_to_uint8(narray, 16, lower, upper)
    elif narray.dtype in [np.uint32, np.float32]:
        narray_uint8 = convert_narray_uintX_to_uint8(narray, 32, lower, upper)
    elif narray.dtype in [np.uint64, np.float64]:
        narray_uint8 = convert_narray_uintX_to_uint8(narray, 64, lower, upper)
    else:
        raise HTTPException(status_code=400, detail="Array conversion not supported")

    try:
        if mode == "L" or narray_uint8.shape[0] == 1:
            # convert to grayscale for single channel
            new_array = narray_uint8[0, :, :]
            pil_image = Image.fromarray(new_array, mode="L")
        else:
            # we need to transpose the array here to make it readable for pillow (width, height, channel)
            narray_uint8 = np.ascontiguousarray(narray_uint8.transpose(1, 2, 0))
            pil_image = Image.fromarray(narray_uint8, mode="RGB")
        return pil_image
    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"Image conversion to Pillow failed: {err}")


def save_rgb_image(pil_image, image_format, image_quality):
    mem = BytesIO()
    pil_image.save(mem, format=image_format, quality=image_quality)
    mem.seek(0)
    return mem


def get_requested_channels_as_rgb_array(narray, image_channels, slide):
    separate_channels = np.vsplit(narray, narray.shape[0])

    temp_array = []
    if image_channels is not None and len(image_channels) == 1:
        # edge case 1: single channel will be converted to a grayscale image
        return separate_channels[image_channels[0]]
    elif image_channels is not None and len(image_channels) == 2:
        # edge case 2: we cast two dedicated image to an rgb image if requested
        temp_array.append(separate_channels[image_channels[0]])
        temp_array.append(separate_channels[image_channels[1]])
        temp_array.append(np.zeros(separate_channels[image_channels[0]].shape))
    else:
        # three or more channels given
        # in this case we simply return the first 3 channels for now
        temp_array = get_multi_channel_as_rgb(separate_channels)

    result = np.concatenate(temp_array, axis=0)
    return result


def get_multi_channel_as_rgb(separate_channels):
    # right now only three channels are considered
    temp_array = []
    for channel in separate_channels:
        if len(temp_array) == 3:
            break
        temp_array.append(channel)
    return temp_array


def get_single_channel(separate_channels, channel, color):
    temp_array = []
    for i in range(3):
        c = color.r if i == 0 else (color.g if i == 1 else color.b)
        temp_channel = separate_channels[channel] * (c / 255)
        temp_array.append(temp_channel)
    return temp_array


def get_requested_channels_as_array(narray, image_channels):
    if narray.shape[0] == len(image_channels):
        return narray

    separate_channels = np.vsplit(narray, narray.shape[0])
    temp_array = []
    for i in image_channels:
        temp_array.append(separate_channels[i])
    result = np.concatenate(temp_array, axis=0)
    return result


def check_complete_region_overlap(slide_info, level, start_x, start_y, size_x, size_y):
    return (
        start_x >= 0
        and start_y >= 0
        and start_x + size_x < slide_info.levels[level].extent.x
        and start_y + size_y < slide_info.levels[level].extent.y
    )


async def get_extended_region(get_region, slide_info, level, start_x, start_y, size_x, size_y,
                              padding_color=None, z=0, icc_intent=None):
    # check overlap of requested region and slide
    overlap = (start_x + size_x > 0 and start_x < slide_info.levels[level].extent.x) and (
        start_y + size_y > 0 and start_y < slide_info.levels[level].extent.y
    )
    # get overlapping region if there is an overlap
    if overlap:
        if start_x < 0:
            region_request_start_x = 0
            overlap_start_x = abs(start_x)
        else:
            region_request_start_x = start_x
            overlap_start_x = 0
        if start_y < 0:
            region_request_start_y = 0
            overlap_start_y = abs(start_y)
        else:
            region_request_start_y = start_y
            overlap_start_y = 0
        overlap_size_x = min(slide_info.levels[level].extent.x - region_request_start_x, size_x - overlap_start_x)
        overlap_size_y = min(slide_info.levels[level].extent.y - region_request_start_y, size_y - overlap_start_y)
        image_region_overlap = await get_region(
            level,
            region_request_start_x,
            region_request_start_y,
            overlap_size_x,
            overlap_size_y,
            padding_color=padding_color,
            z=z,
            icc_intent=icc_intent
        )
    # create empty region based on returned region data type
    if overlap:
        image_region_sample = image_region_overlap
    else:
        image_region_sample = await get_region(0, 0, 0, 1, 1)
    if isinstance(image_region_sample, Image.Image):
        image_region = Image.new("RGB", (size_x, size_y), padding_color)
    else:
        image_region = np.zeros((image_region_sample.shape[0], size_y, size_x), dtype=image_region_sample.dtype)
    # insert overlapping region into empty region
    if overlap:
        if isinstance(image_region_sample, Image.Image):
            image_region.paste(
                image_region_overlap,
                box=(
                    overlap_start_x,
                    overlap_start_y,
                    overlap_start_x + overlap_size_x,
                    overlap_start_y + overlap_size_y,
                ),
            )
        else:
            image_region[
                :,
                overlap_start_y : overlap_start_y + overlap_size_y,
                overlap_start_x : overlap_start_x + overlap_size_x,
            ] = image_region_overlap
    return image_region


def check_complete_tile_overlap(slide_info, level, tile_x, tile_y):
    tile_count_x = int(slide_info.levels[level].extent.x / slide_info.tile_extent.x)
    tile_count_y = int(slide_info.levels[level].extent.y / slide_info.tile_extent.y)
    return tile_x >= 0 and tile_y >= 0 and tile_x < tile_count_x and tile_y < tile_count_y


async def get_extended_tile(get_tile, slide_info, level, tile_x, tile_y, padding_color=None, z=0, icc_intent=None):
    overlap_size_x = slide_info.levels[level].extent.x - tile_x * slide_info.tile_extent.x
    overlap_size_y = slide_info.levels[level].extent.y - tile_y * slide_info.tile_extent.y
    overlap = tile_x >= 0 and tile_y >= 0 and overlap_size_x > 0 and overlap_size_y > 0
    # get overlapping tile if there is an overlap
    if overlap:
        image_tile_overlap = await get_tile(level, tile_x, tile_y, padding_color=padding_color, z=z, icc_intent=icc_intent)
        if isinstance(image_tile_overlap, bytes):
            image_tile_overlap = Image.open(BytesIO(image_tile_overlap))
    # create empty tile based on returned tile data type
    if overlap:
        image_tile_sample = image_tile_overlap
    else:
        image_tile_sample = await get_tile(0, 0, 0)
        if isinstance(image_tile_sample, bytes):
            image_tile_sample = Image.open(BytesIO(image_tile_sample))
    if isinstance(image_tile_sample, Image.Image):
        image_tile = Image.new("RGB", (slide_info.tile_extent.x, slide_info.tile_extent.y), padding_color)
    else:
        image_tile = np.zeros(
            (image_tile_sample.shape[0], slide_info.tile_extent.x, slide_info.tile_extent.y),
            dtype=image_tile_sample.dtype,
        )
    # insert overlapping tile into empty tile
    if overlap:
        if isinstance(image_tile_sample, Image.Image):
            image_tile.paste(
                image_tile_overlap.crop((0, 0, overlap_size_x, overlap_size_y)),
                box=(
                    0,
                    0,
                    overlap_size_x,
                    overlap_size_y,
                ),
            )
        else:
            image_tile[
                :,
                0:overlap_size_y,
                0:overlap_size_x,
            ] = image_tile_overlap[:, 0:overlap_size_y, 0:overlap_size_x]
    return image_tile
