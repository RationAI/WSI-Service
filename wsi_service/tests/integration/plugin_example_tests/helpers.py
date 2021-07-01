import io
import os

import tifffile
from PIL import Image


def make_dir_if_not_exists(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)


def get_image(response):
    return Image.open(io.BytesIO(response.raw.data))


def get_tiff_image(response):
    return tifffile.TiffFile(io.BytesIO(response.raw.data))


def tiff_pixels_equal(tiff_image, pixel_location, testpixel):
    narray = tiff_image.asarray()
    pixel = narray[pixel_location[0]][pixel_location[1]][pixel_location[2]]
    if pixel != testpixel[pixel_location[0]]:
        return False
    return True
