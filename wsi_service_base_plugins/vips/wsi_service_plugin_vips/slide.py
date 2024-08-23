import re
import xml.etree.ElementTree as xml
from threading import Lock

from PIL import Image
import numpy as np
import pyvips
from fastapi import HTTPException
from skimage import transform, util

from wsi_service.models.v3.slide import SlideChannel, SlideColor, SlideExtent, SlideInfo, SlidePixelSizeNm
from wsi_service.singletons import settings
from wsi_service.slide import Slide as BaseSlide
from wsi_service.utils.image_utils import rgba_to_rgb_with_background_color
from wsi_service.utils.slide_utils import get_original_levels, get_rgb_channel_list


class Slide(BaseSlide):
    format_kinds = ["tiffload"]

    async def open(self, filepath):
        self.locker = Lock()
        try:
            self.vips_slide = pyvips.Image.new_from_file(filepath, access='sequential')
            if self.vips_slide.get('vips-loader') != 'tiffload':
                raise HTTPException(
                    status_code=500,
                    detail="Unsupported file format",
                )
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Failed to load tiff file. [{e}]")
        self.slide_info = self.__get_slide_info_tiff()
        # Validate the parsed slide_info to ensure non-zero dimensions
        if self.slide_info.extent.x == 0 or self.slide_info.extent.y == 0:
            raise HTTPException(status_code=500, detail="Parsed slide dimensions are zero.")
        if self.slide_info.tile_extent.x == 0 or self.slide_info.tile_extent.y == 0:
            raise HTTPException(status_code=500, detail="Parsed tile dimensions are zero.")

    async def close(self):
        self.vips_slide = None

    async def get_info(self):
        return self.slide_info

    async def get_region(self, level, start_x, start_y, size_x, size_y, padding_color=None, z=0):
        if padding_color is None:
            padding_color = settings.padding_color

        vips_level = self.__get_vips_level_for_slide_level(level)
        region = vips_level.extract_area(start_x, start_y, size_x, size_y)

        # Ensure the image is in sRGB color space
        if region.interpretation != 'srgb':
            region = region.colourspace('srgb')

        result = np.array(region)

        # Check if the data is float and convert to integers
        if np.issubdtype(result.dtype, np.floating):
            result = (result * 255).astype(np.uint8)

        # Convert grayscale or single-channel to RGB
        if result.ndim == 2:  # Grayscale image
            result = np.stack((result,) * 3, axis=-1)  # Convert grayscale to RGB
        elif result.ndim == 3 and result.shape[2] == 1:  # Single channel
            result = np.concatenate([result] * 3, axis=2)  # Convert single channel to RGB

        return result

    async def get_thumbnail(self, max_x, max_y):
        thumb_level = len(self.slide_info.levels) - 1
        for i, level in enumerate(self.slide_info.levels):
            if level.extent.x < max_x or level.extent.y < max_y:
                thumb_level = i
                break
        level_extent_x = self.slide_info.levels[thumb_level].extent.x
        level_extent_y = self.slide_info.levels[thumb_level].extent.y
        if max_x > max_y:
            max_y = max_y * (level_extent_y / level_extent_x)
        else:
            max_x = max_x * (level_extent_x / level_extent_y)
        # thumbnail_org = self.__get_vips_level_for_slide_level(thumb_level)
        # return np.array(thumbnail_org)

        thumbnail_org = await self.get_region(thumb_level, 0, 0, level_extent_x, level_extent_y, settings.padding_color)
        thumbnail_resized = util.img_as_uint(transform.resize(thumbnail_org, (max_y, max_x, thumbnail_org.shape[2])))
        return thumbnail_resized

    async def get_label(self):
        self.__get_associated_image("label")

    async def get_macro(self):
        self.__get_associated_image("macro")

    async def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0):
        return await self.get_region(
            level,
            tile_x * self.slide_info.tile_extent.x,
            tile_y * self.slide_info.tile_extent.y,
            self.slide_info.tile_extent.x,
            self.slide_info.tile_extent.y,
            padding_color,
        )

    # private

    def __get_associated_image(self, associated_image_name):
        raise HTTPException(
            status_code=404,
            detail=f"Associated image {associated_image_name} does not exist.",
        )

    def __get_color_for_channel(self, channel_index, channel_depth, padding_color):
        if channel_depth == 8:
            if padding_color is None:
                padding_color = settings.padding_color
            rgb_color = padding_color[channel_index if channel_index < 2 else 2]
        else:
            rgb_color = 0
        return rgb_color

    def __get_vips_level_for_slide_level(self, level):
        return pyvips.Image.new_from_file(self.vips_slide.filename, page=level, access='sequential')

    def __get_levels_tiff(self):
        num_levels = self.vips_slide.get("n-pages")
        levels = [self.__get_vips_level_for_slide_level(i) for i in range(num_levels)]
        level_count = len(levels)
        level_dimensions = []
        level_downsamples = []

        for i, item in enumerate(levels):
            level_dimensions.append([item.width, item.height])
            if i > 0:
                level_downsamples.append(level_dimensions[0][0] / item.width)
            else:
                level_downsamples.append(1)

        original_levels = get_original_levels(level_count, level_dimensions, level_downsamples)
        return original_levels

    def __get_slide_info_tiff(self):
        serie = self.vips_slide
        levels = self.__get_levels_tiff()

        try:
            tile_width = serie.get('tile-width') if 'tile-width' in serie.get_fields() else 0
            tile_height = serie.get('tile-height') if 'tile-height' in serie.get_fields() else 0

            if tile_width == 0 or tile_height == 0:
                tile_width, tile_height = self.__infer_tile_size(levels[0])

            slide_info = SlideInfo(
                id="",
                channels=[SlideChannel(id=0, name="Channel 0", color=SlideColor(r=255, g=255, b=255, a=255))],
                channel_depth=8,  # Assuming 8-bit depth for simplicity
                extent=SlideExtent(
                    x=serie.width,
                    y=serie.height,
                    z=1,
                ),
                pixel_size_nm=SlidePixelSizeNm(x=1, y=1),  # Assuming 1nm pixel size for simplicity
                tile_extent=SlideExtent(
                    x=tile_width,
                    y=tile_height,
                    z=1,
                ),
                num_levels=len(levels),
                levels=levels,
                format="tiff",
            )
            return slide_info
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Failed to gather slide infos. [{e}]")


# import asyncio
#
#
# async def main():
#     slide = Slide()
#     await slide.open("/mnt/data/wsi_mask/57f2711b-c8ba-4fd5-be4d-be3ccece71eb/background_mask.tiff")
#
#     data = await slide.get_thumbnail(400, 400)
#
#     from PIL import Image
#     im = Image.fromarray(data, 'RGB')
#     im.save("thumb.jpeg")
#
#     tile = await slide.get_tile(5, 0, 0)
#     im = Image.fromarray(tile, 'RGB')
#     im.save("thumb.jpeg")
#
#
# asyncio.run(main())