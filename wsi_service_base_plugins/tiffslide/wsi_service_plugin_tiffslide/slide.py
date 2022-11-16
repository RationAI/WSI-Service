# import aiofiles
import numpy as np
import tiffslide
from fastapi import HTTPException

from wsi_service.models.v3.slide import SlideExtent, SlideInfo, SlidePixelSizeNm
from wsi_service.singletons import settings
from wsi_service.slide import Slide as BaseSlide
from wsi_service.utils.image_utils import rgba_to_rgb_with_background_color
from wsi_service.utils.slide_utils import get_original_levels, get_rgb_channel_list


class jpeg_tags:
    quantization_tables = b"\xff\xdb"
    huffman_tables = b"\xff\xc4"
    end_of_image = b"\xff\xd9"
    start_of_frame = b"\xff\xc0"
    start_of_scan = b"\xff\xda"


class Slide(BaseSlide):
    supported_vendors = ["aperio", None]

    async def open(self, filepath):
        self.filepath = filepath
        await self.open_slide()
        self.format = self.slide.detect_format(self.filepath)
        self.slide_info = self.__get_slide_info()
        self.is_jpeg_compression = await self.__is_jpeg_compression()

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
        if self.is_jpeg_compression:
            tif_level = self.__get_tif_level_for_slide_level(level)
            page = tif_level.pages[0]
            tile_data = await self.__read_raw_tile(page, tile_x, tile_y)
            tile_data = self.__add_jpeg_headers(page, tile_data)
            return bytes(tile_data)
        else:
            return await self.get_region(
                level,
                tile_x * self.slide_info.tile_extent.x,
                tile_y * self.slide_info.tile_extent.y,
                self.slide_info.tile_extent.x,
                self.slide_info.tile_extent.y,
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

    async def __is_jpeg_compression(self):
        tif_level = self.__get_tif_level_for_slide_level(0)
        page = tif_level.pages[0]
        return page.jpegtables is not None

    def __get_quantization_and_huffman_tables(self, jpegtables):
        start_quantization_tables = jpegtables.find(jpeg_tags.quantization_tables)
        start_huffman_tables = jpegtables.find(jpeg_tags.huffman_tables)
        end_of_image = jpegtables.find(jpeg_tags.end_of_image)
        quantization_tables = jpegtables[start_quantization_tables:start_huffman_tables]
        huffman_tables = jpegtables[start_huffman_tables:end_of_image]
        return quantization_tables, huffman_tables

    async def __read_raw_tile(self, page, tile_x, tile_y):
        image_width = page.keyframe.imagewidth
        tile_width = page.keyframe.tilewidth
        tile_per_line = int(np.ceil(image_width / tile_width))
        index = int(tile_y * tile_per_line + tile_x)
        offset = page.dataoffsets[index]
        bytecount = page.databytecounts[index]
        # async with aiofiles.open(self.filepath, mode="rb") as f:
        #     await f.seek(offset)
        #     data = bytearray(await f.read(bytecount))
        self.slide._tifffile.filehandle.seek(offset)
        data = bytearray(self.slide._tifffile.filehandle.read(bytecount))
        return data

    def __add_jpeg_headers(self, page, data):
        (
            quantization_tables,
            huffman_tables,
        ) = self.__get_quantization_and_huffman_tables(page.jpegtables)
        # add quantization tables
        pos = data.find(jpeg_tags.start_of_frame)
        data[pos:pos] = quantization_tables
        # add huffman tables
        pos = data.find(jpeg_tags.start_of_scan)
        data[pos:pos] = huffman_tables
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
        # 01 = YCbCr
        # 02 = YCCK
        pos = data.find(jpeg_tags.quantization_tables)
        data[pos:pos] = bytearray.fromhex("ff ee 00 0e 41 64 6f 62 65 0064 00 00 00 00 00")
        return data
