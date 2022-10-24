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
            tile_extent=SlideExtent(x=256, y=256, z=1),
            levels=[SlideLevel(extent=SlideExtent(x=width, y=height, z=1), downsample_factor=1.0)],
        )

    async def close(self):
        self.slide_image.close()

    async def get_info(self):
        return self.slide_info

    async def get_region(self, level, start_x, start_y, size_x, size_y, padding_color=None, z=0):
        if padding_color is None:
            padding_color = settings.padding_color
        if level != 0:
            raise HTTPException(
                status_code=422,
                detail=f"""The requested pyramid level is not available.
                    The coarsest available level is {len(self.slide_info.levels) - 1}.""",
            )
        region = Image.new("RGB", (size_x, size_y), padding_color)
        # check overlap of requested region with actual image
        overlap = (start_x + size_x > 0 and start_x < self.slide_info.extent.x) and (
            start_y + size_y > 0 and start_y < self.slide_info.extent.y
        )
        if overlap:
            if start_x < 0:
                crop_start_x = 0
                overlap_start_x = abs(start_x)
            else:
                crop_start_x = start_x
                overlap_start_x = 0
            if start_y < 0:
                crop_start_y = 0
                overlap_start_y = abs(start_y)
            else:
                crop_start_y = start_y
                overlap_start_y = 0
            overlap_size_x = min(self.slide_info.extent.x - crop_start_x, size_x)
            overlap_size_y = min(self.slide_info.extent.y - crop_start_y, size_y)
            cropped_image = self.slide_image.crop(
                (
                    crop_start_x,
                    crop_start_y,
                    crop_start_x + overlap_size_x,
                    crop_start_y + overlap_size_y,
                )
            )
            region.paste(
                cropped_image,
                box=(
                    overlap_start_x,
                    overlap_start_y,
                    overlap_start_x + overlap_size_x,
                    overlap_start_y + overlap_size_y,
                ),
            )
        return region

    async def get_thumbnail(self, max_x, max_y):
        thumbnail = self.slide_image.copy()
        thumbnail.thumbnail((max_x, max_y))
        return thumbnail

    async def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0):
        return await self.get_region(
            level,
            tile_x * self.slide_info.tile_extent.x,
            tile_y * self.slide_info.tile_extent.y,
            self.slide_info.tile_extent.x,
            self.slide_info.tile_extent.y,
            padding_color=padding_color,
            z=z,
        )

    def _get_associated_image(self, associated_image_name):
        raise HTTPException(
            status_code=404,
            detail=f"Associated image {associated_image_name} does not exist.",
        )

    async def get_label(self):
        self._get_associated_image("label")

    async def get_macro(self):
        self._get_associated_image("macro")
