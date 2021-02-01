from io import BytesIO

import numpy as np
import PIL


def rgba_to_rgb_with_background_color(image_rgba, background_color=(255, 255, 255)):
    image_rgb = PIL.Image.new("RGB", image_rgba.size, background_color)
    image_rgb.paste(image_rgba, mask=image_rgba.split()[3])
    return image_rgb


def convert_narray_uintX_to_uint8(array, exp=16, lower=None, upper=None):
    if not exp in [8, 16, 32, 64]:
        raise ValueError("Only exponent in range [8, 16, 32, 64] supported")
    if lower is not None and not (0 <= lower < 2 ** exp):
        raise ValueError(f"lower bound must be between 0 and 2**{exp}")
    if upper is not None and not (0 <= upper < 2 ** exp):
        raise ValueError(f"upper bound must be between 0 and 2**{exp}")
    if lower is None:
        lower = np.min(array)
    if upper is None:
        upper = np.max(array)

    temp_array = array / upper
    temp_array = temp_array * 255
    return temp_array.astype(np.uint8)


def covert_int_to_rgba_array(i):
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


def convert_narray_to_pil_image(narray):
    if narray.dtype == np.uint8:
        narray_uint8 = narray
    elif narray.dtype == np.uint16:
        narray_uint8 = convert_narray_uintX_to_uint8(narray, 16)
    elif narray.dtype in [np.uint32, np.float32]:
        narray_uint8 = convert_narray_uintX_to_uint8(narray, 32)
    elif narray.dtype in [np.uint64, np.float64]:
        narray_uint8 = convert_narray_uintX_to_uint8(narray, 64)
    else:
        raise NotImplementedError("Array conversion not supported")

    # we need to transpose the array here to make it readable for pillow (width, height, channel)
    narray_uint8 = np.ascontiguousarray(narray_uint8.transpose(1, 2, 0))
    pil_image = PIL.Image.fromarray(narray_uint8, mode="RGB")
    return pil_image


def save_rgb_image(pil_image, image_format, image_quality):
    mem = BytesIO()
    if image_format == "png":
        pil_image.save(mem, format=image_format, optimize=(image_quality > 0))
    else:
        pil_image.save(mem, format=image_format, quality=image_quality)
    mem.seek(0)
    return mem


def convert_narray_to_rgb_8bit(narray, image_channels):
    separate_channels = np.vsplit(narray, narray.shape[0])

    if len(image_channels) > 3:
        # handle case when more than 3 channels
        result = separate_channels
    else:
        temp_array = []
        for i in range(3):
            if i in image_channels:
                temp_array.append(separate_channels[i])
            else:
                temp_array.append(np.zeros(separate_channels[0].shape))

    result = np.concatenate(temp_array, axis=0)
    return result
