import numpy as np
import tiffslide
from fastapi import HTTPException

from wsi_service.models.v3.slide import SlideExtent, SlideInfo, SlidePixelSizeNm
from wsi_service.singletons import settings
from wsi_service.slide import Slide as BaseSlide
from wsi_service.utils.image_utils import rgba_to_rgb_with_background_color
from wsi_service.utils.slide_utils import get_original_levels, get_rgb_channel_list, get_tile_width


class Slide(BaseSlide):
    supported_vendors = ["aperio", "hamamatsu", None]

    async def open(self, filepath):
        self.filepath = filepath
        await self.open_slide()
        self.format = self.slide.detect_format(self.filepath)
        self.slide_info = self.__get_slide_info()
        self.is_jpeg_compression = self.__is_jpeg_compression()
        self.color_transform = self.__get_color_transform()

    async def open_slide(self):
        try:
            self.slide = tiffslide.TiffSlide(self.filepath)
        except tiffslide.TiffFileError as e:
            raise HTTPException(status_code=500, detail=f"TiffFileError: {e}")

    async def close(self):
        self.slide.close()

    async def get_info(self):
        return self.slide_info

    async def get_region(self, level, start_x, start_y, size_x, size_y, padding_color=None, z=0):
        if padding_color is None:
            padding_color = settings.padding_color
        downsample_factor = self.slide_info.levels[level].downsample_factor
        level_0_location = (
            (int)(start_x * downsample_factor),
            (int)(start_y * downsample_factor),
        )
        level_0_location = self.__adapt_level_0_location(level_0_location, downsample_factor, start_x, start_y)
        try:
            img = self.slide.read_region(level_0_location, level, (size_x, size_y))
        except tiffslide.TiffFileError as e:
            raise HTTPException(status_code=500, detail=f"TiffFileError: {e}")
        rgb_img = rgba_to_rgb_with_background_color(img, padding_color)
        return rgb_img

    async def get_thumbnail(self, max_x, max_y):
        if not hasattr(self, "thumbnail"):
            try:
                self.thumbnail = self.__get_associated_image("thumbnail")
            except HTTPException:
                self.thumbnail = await self.__get_thumbnail(settings.max_thumbnail_size, settings.max_thumbnail_size)
        thumbnail = self.thumbnail.copy()
        thumbnail.thumbnail((max_x, max_y))
        return thumbnail

    async def get_label(self):
        return self.__get_associated_image("label")

    async def get_macro(self):
        return self.__get_associated_image("macro")

    async def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0):
        # todo: this returns padded tile with black colors
        # if self.is_jpeg_compression:
        #     tif_level = self.__get_tif_level_for_slide_level(level)
        #     page = tif_level.pages[0]
        #     tile_data = await self.__read_raw_tile(page, tile_x, tile_y)
        #     self.__add_jpeg_headers(page, tile_data, self.color_transform)
        #     return bytes(tile_data)
        # else:
            tile_width, tile_height = get_tile_width(self.slide_info, level, tile_x, tile_y)

            return await self.get_region(
                level,
                tile_x * self.slide_info.tile_extent.x,
                tile_y * self.slide_info.tile_extent.y,
                tile_width,
                tile_height,
                padding_color,
            )

    # private

    def __get_tif_level_for_slide_level(self, level):
        slide_level = self.slide_info.levels[level]
        for level in self.slide._tifffile.series[0].levels:
            if level.shape[1] == slide_level.extent.x and level.shape[0] == slide_level.extent.y:
                return level

    def __get_associated_image(self, associated_image_name):
        if associated_image_name not in self.slide.associated_images:
            raise HTTPException(
                status_code=404,
                detail=f"Associated image {associated_image_name} does not exist.",
            )
        associated_image_rgba = self.slide.associated_images[associated_image_name]
        return associated_image_rgba.convert("RGB")

    def __get_levels(self):
        original_levels = get_original_levels(
            self.slide.level_count,
            self.slide.level_dimensions,
            self.slide.level_downsamples,
        )
        return original_levels

    def __get_pixel_size(self):
        if self.slide.properties[tiffslide.PROPERTY_NAME_VENDOR] in self.supported_vendors:
            pixel_size_nm_x = 1000.0 * float(self.slide.properties[tiffslide.PROPERTY_NAME_MPP_X])
            pixel_size_nm_y = 1000.0 * float(self.slide.properties[tiffslide.PROPERTY_NAME_MPP_Y])
        else:
            SlidePixelSizeNm()
        return SlidePixelSizeNm(x=pixel_size_nm_x, y=pixel_size_nm_y)

    def __get_tile_extent(self):
        tile_height = 256
        tile_width = 256
        if (
            "tiffslide.level[0].tile-height" in self.slide.properties
            and "tiffslide.level[0].tile-width" in self.slide.properties
        ):
            # some tiles can have an unequal tile height and width that can cause problems in the slide viewer
            # since the tile route is used for viewing only, we provide the default tile width and height
            temp_height = self.slide.properties["tiffslide.level[0].tile-height"]
            temp_width = self.slide.properties["tiffslide.level[0].tile-width"]
            if temp_height == temp_width:
                tile_height = temp_height
                tile_width = temp_width

        return SlideExtent(x=tile_width, y=tile_height, z=1)

    def __get_slide_info(self):
        try:
            levels = self.__get_levels()
            slide_info = SlideInfo(
                id="",
                channels=get_rgb_channel_list(),  # rgb channels
                channel_depth=8,  # 8bit each channel
                extent=SlideExtent(
                    x=self.slide.dimensions[0],
                    y=self.slide.dimensions[1],
                    z=1,
                ),
                pixel_size_nm=self.__get_pixel_size(),
                tile_extent=self.__get_tile_extent(),
                num_levels=len(levels),
                levels=levels,
                format=self.format,
            )
            return slide_info
        except HTTPException as e:
            raise HTTPException(status_code=404, detail=f"Failed to gather slide infos. [{e.detail}]")
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Failed to gather slide infos. [{e}]")

    async def __get_thumbnail(self, max_x, max_y):
        level = self.__get_best_level_for_thumbnail(max_x, max_y)

        try:
            thumbnail = await self.get_region(
                level,
                0,
                0,
                self.slide_info.levels[level].extent.x,
                self.slide_info.levels[level].extent.y,
            )
        except HTTPException as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract thumbnail from WSI [{e.detail}].",
            )

        thumbnail.thumbnail((max_x, max_y))
        return thumbnail

    def __get_best_level_for_thumbnail(self, max_x, max_y):
        best_level = 0
        for level in self.slide_info.levels:
            if level.extent.x < max_x and level.extent.y < max_y:
                return best_level - 1
            best_level += 1
        return best_level - 1

    def __is_jpeg_compression(self):
        tif_level = self.__get_tif_level_for_slide_level(0)
        page = tif_level.pages[0]
        return page.jpegtables is not None

    def __get_color_transform(self):
        tif_level = self.__get_tif_level_for_slide_level(0)
        page = tif_level.pages[0]
        color_transform = "Unknown"
        if page.photometric == 6:
            color_transform = "YCbCr"
        return color_transform

    async def __read_raw_tile(self, page, tile_x, tile_y):
        image_width = page.keyframe.imagewidth
        tile_width = page.keyframe.tilewidth
        tile_per_line = int(np.ceil(image_width / tile_width))
        index = int(tile_y * tile_per_line + tile_x)
        offset = page.dataoffsets[index]
        bytecount = page.databytecounts[index]
        self.slide._tifffile.filehandle.seek(offset)
        data = self.slide._tifffile.filehandle.read(bytecount)
        return bytearray(data)

    def __add_jpeg_headers(self, page, data, color_transform):
        # add jpeg tables
        pos = data.find(b"\xFF\xDA")
        data[pos:pos] = page.jpegtables[2:-2]
        # check missing huffman tables
        if data.find(b"\xFF\xC4") < 0:
            data[pos:pos] = self.__get_default_huffman_tables()
        # add APP14 data
        #
        # Marker: ff ee
        # Length (14 bytes): 00 0e
        # Adobe (ASCI): 41 64 6f 62 65
        # Version (100): 00 64
        # Flags0: 00 00
        # Flags1: 00 00
        # Color transform:
        # 00 = Unknown (RGB or CMYK)
        color_transform_value = b"\x00"
        # 01 = YCbCr
        if color_transform == "YCbCr":
            color_transform_value = b"\x01"
        data[pos:pos] = b"\xFF\xEE\x00\x0E\x41\x64\x6F\x62\x65\x00\x64\x00\x00\x00\x00" + color_transform_value

    def __adapt_level_0_location(self, level_0_location, downsample_factor, start_x, start_y):
        # adapting level_0_location to maintain better compatibility with openslide
        # check issue: https://github.com/bayer-science-for-a-better-life/tiffslide/issues/63
        tiffslide_start_x = int(level_0_location[0] / downsample_factor)
        tiffslide_start_y = int(level_0_location[1] / downsample_factor)
        if tiffslide_start_x != start_x:
            level_0_location = (
                (int)(level_0_location[0] + abs(tiffslide_start_x - start_x) * downsample_factor),
                level_0_location[1],
            )
        if tiffslide_start_y != start_y:
            level_0_location = (
                level_0_location[0],
                (int)(level_0_location[1] + abs(tiffslide_start_y - start_y) * downsample_factor),
            )
        return level_0_location

    def __get_default_huffman_tables(
        self,
    ):
        return b"\xFF\xC4\x00\x1F\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\xFF\xC4\x00\xB5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01\x7d\x01\x02\x03\x00\x04\x11\x05\x12\x21\x31\x41\x06\x13\x51\x61\x07\x22\x71\x14\x32\x81\x91\xa1\x08\x23\x42\xb1\xc1\x15\x52\xd1\xf0\x24\x33\x62\x72\x82\x09\x0a\x16\x17\x18\x19\x1a\x25\x26\x27\x28\x29\x2a\x34\x35\x36\x37\x38\x39\x3a\x43\x44\x45\x46\x47\x48\x49\x4a\x53\x54\x55\x56\x57\x58\x59\x5a\x63\x64\x65\x66\x67\x68\x69\x6a\x73\x74\x75\x76\x77\x78\x79\x7a\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa"
