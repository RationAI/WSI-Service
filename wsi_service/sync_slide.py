import asyncio
from io import BytesIO

import numpy as np
from PIL import Image

from wsi_service.plugins import load_slide


class SyncSlide:
    def __init__(self, filepath, plugin=None):
        self.loop = asyncio.get_event_loop()
        self.async_slide = self.loop.run_until_complete(load_slide(filepath, plugin=plugin))

    def get_info(self):
        return self.loop.run_until_complete(self.async_slide.get_info())

    def get_thumbnail(self, max_x, max_y):
        return self._get_pil(self.loop.run_until_complete(self.async_slide.get_thumbnail(max_x, max_y)))

    def get_label(self):
        return self._get_pil(self.loop.run_until_complete(self.async_slide.get_label()))

    def get_macro(self):
        return self._get_pil(self.loop.run_until_complete(self.async_slide.get_macro()))

    def get_region(self, level, start_x, start_y, size_x, size_y, z=0):
        return self._get_pil(
            self.loop.run_until_complete(self.async_slide.get_region(level, start_x, start_y, size_x, size_y, z=z))
        )

    def get_tile(self, level, tile_x, tile_y, z=0):
        return self._get_pil(self.loop.run_until_complete(self.async_slide.get_tile(level, tile_x, tile_y, z=z)))

    def _get_pil(self, image):
        if isinstance(image, Image.Image):
            return image
        if isinstance(image, bytes):
            return Image.open(BytesIO(image))
        if isinstance(image, (np.ndarray, np.generic)):
            return Image.fromarray(image)
