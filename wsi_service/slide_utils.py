import math

import openslide
import PIL
from fastapi import HTTPException

from wsi_service.models.slide import Extent, Level, PixelSizeNm, SlideInfo


def check_generated_levels_for_originals(original_levels, generated_levels):
    for generated_level in generated_levels:
        for original_level in original_levels:
            if (
                original_level.extent.x == generated_level.extent.x
                and original_level.extent.y == generated_level.extent.y
            ):
                generated_level.generated = False
    return generated_level


def rgba_to_rgb_with_background_color(image_rgba, background_color=(255, 255, 255)):
    image_rgb = PIL.Image.new("RGB", image_rgba.size, background_color)
    image_rgb.paste(image_rgba, mask=image_rgba.split()[3])
    return image_rgb
