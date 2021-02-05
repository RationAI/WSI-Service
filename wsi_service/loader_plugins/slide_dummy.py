import math

import PIL

import wsi_service.slide_utils
from wsi_service.image_utils import rgba_to_rgb_with_background_color
from wsi_service.models.slide import SlideInfo
from wsi_service.slide import Slide
from wsi_service.slide_utils import Extent, Level, PixelSizeNm


class DummySlide(Slide):
    loader_name = "DummySlide"

    def __init__(self, filepath, slide_id):
        self.slide_info = SlideInfo(
            id="id",
            channels=[],
            channel_depth=8,
            extent=Extent(x=0, y=0, z=0),
            num_levels=0,
            pixel_size_nm=PixelSizeNm(x=0, y=0),
            tile_extent=Extent(x=0, y=0, z=0),
            levels=[Level(extent=Extent(x=0, y=0, z=0), downsample_factor=0, generated=True)],
        )

    def close(self):
        pass

    def get_info(self):
        return self.slide_info

    def get_region(self, level, start_x, start_y, size_x, size_y):
        rgb_img = PIL.Image.new("RGB", (size_x, size_y), color="red")
        return rgb_img

    def get_thumbnail(self, max_x, max_y):
        rgb_img = PIL.Image.new("RGB", (max_x, max_y), color="red")
        return rgb_img

    def _get_associated_image(self, associated_image_name):
        rgb_img = PIL.Image.new("RGB", (10, 10), color="red")
        return rgb_img

    def get_label(self):
        rgb_img = PIL.Image.new("RGB", (10, 10), color="red")
        return rgb_img

    def get_macro(self):
        rgb_img = PIL.Image.new("RGB", (10, 10), color="red")
        return rgb_img

    def get_tile(self, level, tile_x, tile_y):
        return self.get_region(
            level,
            tile_x * self.slide_info.tile_extent.x,
            tile_y * self.slide_info.tile_extent.y,
            self.slide_info.tile_extent.x,
            self.slide_info.tile_extent.y,
        )
