from io import BytesIO

import numpy as np
from fastapi import HTTPException
from PIL import Image


def rgba_to_rgb_with_background_color(image_rgba, padding_color, size=None, paste_size=None, paste_start=None):
    size = size if size else image_rgba.size
    paste_size = paste_size if paste_size else size
    image_rgb = Image.new("RGB", size, padding_color)
    if image_rgba is None:
        return image_rgb
    elif image_rgba.info.get("transparency", None) is not None or image_rgba.mode == "RGBA":
        image_rgb.paste(image_rgba, mask=image_rgba.split()[3], box=(0, 0, paste_size[0], paste_size[1]))
    elif image_rgba.mode == "RGB":
        image_rgb.paste(image_rgba, box=paste_start)

    else:
        raise HTTPException(400, "Raw image data has unsupported image format!")
    return image_rgb


def convert_narray_uintX_to_uint8(array, exp=16, lower=None, upper=None):
    if exp not in [8, 16, 32, 64]:
        raise ValueError("Only exponent in range [8, 16, 32, 64] supported")
    if lower is not None and not (0 <= lower < 2**exp):
        raise ValueError(f"lower bound must be between 0 and 2**{exp}")
    if upper is not None and not (0 <= upper < 2**exp):
        raise ValueError(f"upper bound must be between 0 and 2**{exp}")
    if lower is None:
        lower = 0
    if upper is None:
        # default color mapping
        if exp == 8:
            return array
        elif exp == 16:
            upper = (2**exp) / 4
        else:
            upper = (2**exp) / (exp / 2)

    temp_array = array / upper if upper != 0 else array
    temp_array = temp_array * 255
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
        if mode == "L":
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
