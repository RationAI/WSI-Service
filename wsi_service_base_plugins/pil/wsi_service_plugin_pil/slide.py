from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from wsi_service.models.v3.slide import SlideExtent, SlideInfo, SlideLevel, SlidePixelSizeNm
from wsi_service.singletons import settings
from wsi_service.slide import Slide as BaseSlide
from wsi_service.utils.slide_utils import get_rgb_channel_list


class Slide(BaseSlide):
    async def open(self, filepath):
        try:
            self.slide_image = Image.open(filepath)
        except UnidentifiedImageError:
            raise HTTPException(status_code=500, detail="PIL Unidentified Image Error")
        self.slide_image = Image.open(filepath).convert("RGB")
        width, height = self.slide_image.size


        channels = get_rgb_channel_list()
        self.slide_info = SlideInfo(
            id="",
            channels=channels,
            channel_depth=8,
            extent=SlideExtent(x=width, y=height, z=1),
            num_levels=1,
            pixel_size_nm=SlidePixelSizeNm(x=-1, y=-1),  # pixel size unknown
            tile_extent=SlideExtent(x=width, y=height, z=1) if width < 5000 and height < 5000 else SlideExtent(x=1024, y=1024, z=1),
            levels=[SlideLevel(extent=SlideExtent(x=width, y=height, z=1), downsample_factor=1.0)],
        )

    async def close(self):
        self.slide_image.close()

    async def get_info(self):
        return self.slide_info

    async def get_region(self, level, start_x, start_y, size_x, size_y, padding_color=None, z=0, icc_intent=None):
        if padding_color is None:
            padding_color = settings.padding_color
        region = self.slide_image.crop(
            (
                start_x,
                start_y,
                start_x + size_x,
                start_y + size_y,
            )
        )
        return region

    async def get_thumbnail(self, max_x, max_y, icc_intent=None):
        thumbnail = self.slide_image.copy()
        thumbnail.thumbnail((max_x, max_y))
        return thumbnail

    async def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0, icc_intent=None):
        return await self.get_region(
            level,
            tile_x * self.slide_info.tile_extent.x,
            tile_y * self.slide_info.tile_extent.y,
            self.slide_info.tile_extent.x,
            self.slide_info.tile_extent.y,
            padding_color=padding_color,
            z=z,
            icc_intent=icc_intent
        )

    async def get_label(self):
        self._get_associated_image("label")

    async def get_macro(self, icc_intent=None):
        self._get_associated_image("macro")

    async def get_icc_profile(self):
        raise HTTPException(404, "Icc profile not supported.")

    # private

    def _get_associated_image(self, associated_image_name):
        raise HTTPException(
            status_code=404,
            detail=f"Associated image {associated_image_name} does not exist.",
        )