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


def covert_int_to_rgba_array(i):
    return [(i >> 24) & 0xFF, (i >> 16) & 0xFF, (i >> 8) & 0xFF, i & 0xFF]


def convert_rgba_array_to_int(rgba):
    return int.from_bytes(rgba, byteorder="big", signed=True)
