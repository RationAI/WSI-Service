from io import BytesIO

import numpy as np
import PIL


def rgba_to_rgb_with_background_color(image_rgba, background_color=(255, 255, 255)):
    image_rgb = PIL.Image.new("RGB", image_rgba.size, background_color)
    image_rgb.paste(image_rgba, mask=image_rgba.split()[3])
    return image_rgb


def convert_narray_uint16_to_uint8(array, lower=None, upper=None):
    if lower is not None and not (0 <= lower < 2 ** 16):
        raise ValueError("lower bound must be between 0 and 2**16")
    if upper is not None and not (0 <= upper < 2 ** 16):
        raise ValueError("upper bound must be between 0 and 2**16")
    if lower is None:
        lower = np.min(array)
    if upper is None:
        upper = np.max(array)

    scale = 255 / (upper - lower)
    temp_array = (array - upper) * scale + lower
    return (temp_array.clip(lower, upper) + 0.5).astype(np.uint8)


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


def convert_narray_to_pil_image(narray):
    narray_uint8 = convert_narray_uint16_to_uint8(narray)
    # we need to transpose the array here to make it readable for pillow (width, height, channel)
    narray_uint8 = np.ascontiguousarray(narray_uint8.transpose(1, 2, 0))
    pil_image = PIL.Image.fromarray(narray_uint8)
    return pil_image


def save_rgb_image(pil_image, image_format, image_quality):
    mem = BytesIO()
    if image_format == "png":
        pil_image.save(mem, format=image_format, optimize=(image_quality > 0))
    else:
        pil_image.save(mem, format=image_format, quality=image_quality)
    mem.seek(0)
    return mem
