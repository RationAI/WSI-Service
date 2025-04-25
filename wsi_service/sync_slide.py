import asyncio
from io import BytesIO

import numpy as np
from PIL import Image

from wsi_service.plugins import load_slide
from wsi_service.utils.image_utils import (
    check_complete_region_overlap,
    check_complete_tile_overlap,
    get_extended_region,
    get_extended_tile,
)
from wsi_service.singletons import settings


class Slide:
    def __init__(self, filepath, plugin=None):
        self.async_slide = asyncio.run(load_slide(filepath, plugin=plugin))
        self.slide_info = asyncio.run(self.async_slide.get_info())

    def get_info(self):
        return self.slide_info

    def get_thumbnail(self, max_x, max_y):
        return self._to_numpy_array(asyncio.run(self.async_slide.get_thumbnail(max_x, max_y)))

    def get_label(self):
        return self._to_numpy_array(asyncio.run(self.async_slide.get_label()))

    def get_macro(self):
        return self._to_numpy_array(asyncio.run(self.async_slide.get_macro()))

    def get_region(self, level, start_x, start_y, size_x, size_y, padding_color=None, z=0):
        if check_complete_region_overlap(self.slide_info, level, start_x, start_y, size_x, size_y):
            region = asyncio.run(
                self.async_slide.get_region(level, start_x, start_y, size_x, size_y, padding_color=padding_color, z=z)
            )
        else:
            region = asyncio.run(
                get_extended_region(
                    self.async_slide.get_region,
                    self.slide_info,
                    level,
                    start_x,
                    start_y,
                    size_x,
                    size_y,
                    padding_color=padding_color,
                    z=z,
                )
            )
        return self._to_numpy_array(region)

    def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0):
        if not settings.get_tile_apply_padding or check_complete_tile_overlap(self.slide_info, level, tile_x, tile_y):
            tile = asyncio.run(self.async_slide.get_tile(level, tile_x, tile_y, padding_color=padding_color, z=z))
        else:
            tile = asyncio.run(
                get_extended_tile(
                    self.async_slide.get_tile, self.slide_info, level, tile_x, tile_y, padding_color=padding_color, z=z
                )
            )
        return self._to_numpy_array(tile)

    def _to_numpy_array(self, data):
        if isinstance(data, Image.Image):
            return np.array(data)
        if isinstance(data, bytes):
            return np.array(Image.open(BytesIO(data)))
        if isinstance(data, (np.ndarray, np.generic)):
            return data
