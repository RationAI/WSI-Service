import re
import xml.etree.ElementTree as xml
from threading import Lock

import numpy as np
import tifffile
from fastapi import HTTPException
from skimage import transform, util

from wsi_service.models.v3.slide import SlideChannel, SlideColor, SlideExtent, SlideInfo, SlidePixelSizeNm
from wsi_service.singletons import settings
from wsi_service.slide import Slide as BaseSlide
from wsi_service.utils.image_utils import convert_int_to_rgba_array
from wsi_service.utils.slide_utils import get_original_levels


class Slide(BaseSlide):
    format_kinds = ["OME"]

    async def open(self, filepath):
        self.locker = Lock()
        try:
            self.tif_slide = tifffile.TiffFile(filepath)
            if str(self.tif_slide.series[0].kind).upper() not in self.format_kinds:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unsupported file format ({self.tif_slide.series[0].kind})",
                )
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Failed to load tiff file. [{e}]")
        # read pixel sizes from xml image description
        try:
            self.ome_metadata = self.tif_slide.ome_metadata
            self.parsed_metadata = xml.fromstring(self.ome_metadata)
        except Exception as ex:
            raise HTTPException(status_code=400, detail=f"Could not obtain ome metadata ({ex})")
        self.slide_info = self.__get_slide_info_ome_tif()

    async def close(self):
        self.tif_slide.close()

    async def get_info(self):
        return self.slide_info

    async def get_region(self, level, start_x, start_y, size_x, size_y, padding_color=None, z=0, icc_intent=None):
        if padding_color is None:
            padding_color = settings.padding_color
        level_slide = self.slide_info.levels[level]
        result_array = []
        tif_level = self.__get_tif_level_for_slide_level(level_slide)
        for i, page in enumerate(tif_level.pages):
            temp_channel = self.__read_region_of_page(page, i, start_y, start_x, size_y, size_x, padding_color)
            result_array.append(temp_channel)
        result = np.concatenate(result_array, axis=0)[:, :, :, 0]
        return result

    async def get_thumbnail(self, max_x, max_y, icc_intent=None):
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
        thumbnail_org = await self.get_region(thumb_level, 0, 0, level_extent_x, level_extent_y,
                                              settings.padding_color, 0, icc_intent)
        thumbnail_resized = util.img_as_uint(transform.resize(thumbnail_org, (thumbnail_org.shape[0], max_y, max_x)))
        return thumbnail_resized

    async def get_label(self):
        self.__get_associated_image("label")

    async def get_macro(self, icc_intent=None):
        self.__get_associated_image("macro")

    async def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0, icc_intent=None):
        return await self.get_region(
            level,
            tile_x * self.slide_info.tile_extent.x,
            tile_y * self.slide_info.tile_extent.y,
            self.slide_info.tile_extent.x,
            self.slide_info.tile_extent.y,
            padding_color,
            icc_intent
        )

    async def get_icc_profile(self):
        raise HTTPException(404, "Icc profile not supported.")

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
            # when image depth is higher than 8bit we set default value to zero to make background black:
            # currently channels with more than 8bits bitness are mapped to rgb by distributing color values
            # depending on lowest and highest intensity. therefore mapping colors back and forth will
            # result in undefined behaviour of the padding color
            rgb_color = 0
        return rgb_color

    def __get_tif_level_for_slide_level(self, slide_level):
        for level in self.tif_slide.series[0].levels:
            if level.shape[1] == slide_level.extent.y:
                return level

    def __read_region_of_page(self, page, channel_index, start_x, start_y, size_x, size_y, padding_color):
        page_frame = page.keyframe

        if not page_frame.is_tiled:
            result = self.__read_region_of_page_untiled(
                page, channel_index, start_x, start_y, size_x, size_y, padding_color
            )
            if result.size == 0:
                result = np.full(
                    (size_x, size_y),
                    self.__get_color_for_channel(channel_index, self.slide_info.channel_depth, padding_color),
                    dtype=page_frame.dtype,
                )
        else:
            result = self.__read_region_of_page_tiled(
                page, channel_index, start_x, start_y, size_x, size_y, padding_color
            )
            if result.size == 0:
                result = np.full(
                    (page_frame.imagedepth, size_x, size_y, page_frame.samplesperpixel),
                    self.__get_color_for_channel(channel_index, self.slide_info.channel_depth, padding_color),
                    dtype=page_frame.dtype,
                )

        return result

    def __read_region_of_page_untiled(self, page, channel_index, start_x, start_y, size_x, size_y, padding_color):
        page_frame = page.keyframe
        page_width, page_height = page_frame.imagewidth, page_frame.imagelength
        page_array = page.asarray()

        new_height = page_height - start_x if (start_x + size_x > page_height) else size_x
        new_width = page_width - start_y if (start_y + size_y > page_width) else size_y

        out = np.full(
            (size_x, size_y),
            self.__get_color_for_channel(channel_index, self.slide_info.channel_depth, padding_color),
            dtype=page_frame.dtype,
        )

        out[0:new_height, 0:new_width] = page_array[start_x : start_x + new_height, start_y : start_y + new_width]
        return np.expand_dims(np.expand_dims(out, axis=0), axis=3)

    def __read_region_of_page_tiled(self, page, channel_index, start_x, start_y, size_x, size_y, padding_color):
        page_frame = page.keyframe
        image_width, image_height = page_frame.imagewidth, page_frame.imagelength

        tile_width, tile_height = page_frame.tilewidth, page_frame.tilelength
        end_x = (start_x + size_x) if (start_x + size_x) < image_height else image_height
        end_y = (start_y + size_y) if (start_y + size_y) < image_width else image_width

        start_tile_x0, start_tile_y0 = start_x // tile_height, start_y // tile_width
        end_tile_xn, end_tile_yn = np.ceil([end_x / tile_height, end_y / tile_width]).astype(int)

        tile_per_line = int(np.ceil(image_width / tile_width))

        # initialize array with size of all relevant tiles
        out = np.full(
            (
                page_frame.imagedepth,
                (end_tile_xn - start_tile_x0) * tile_height,
                (end_tile_yn - start_tile_y0) * tile_width,
                page_frame.samplesperpixel,
            ),
            self.__get_color_for_channel(channel_index, self.slide_info.channel_depth, padding_color),
            dtype=page_frame.dtype,
        )
        fh = page.parent.filehandle

        if fh is None:
            raise HTTPException(
                status_code=422,
                detail="Could not read from tiff file. File handle is null",
            )

        jpegtables = page.jpegtables
        if jpegtables is not None:
            jpegtables = jpegtables.value

        used_offsets = []
        # iterate through tiles starting at the top left to the bottom right
        for i in range(start_tile_x0, end_tile_xn):
            for j in range(start_tile_y0, end_tile_yn):
                with self.locker:
                    index = int(i * tile_per_line + j)

                    if len(page.dataoffsets) <= index:
                        continue

                    offset = page.dataoffsets[index]
                    bytecount = page.databytecounts[index]

                    if offset in used_offsets:
                        continue

                    used_offsets.append(offset)

                    # search to tile offset and read image tile
                    fh.seek(offset)
                    if fh.tell() != offset:
                        raise HTTPException(status_code=500, detail="Failed reading to tile offset")
                    data = fh.read(bytecount)
                    tile, _, _ = page.decode(data, index, jpegtables=jpegtables)

                    # insert tile in temporary output array
                    tile_position_i = (i - start_tile_x0) * tile_height
                    tile_position_j = (j - start_tile_y0) * tile_width

                    out[
                        :,
                        tile_position_i : tile_position_i + tile_height,
                        tile_position_j : tile_position_j + tile_width :,
                    ] = tile

        # determine the new start positions of our region
        new_start_x = start_x - start_tile_x0 * tile_height
        new_start_y = start_y - start_tile_y0 * tile_width

        # restrict the output array to the requested region
        result = out[:, new_start_x : new_start_x + size_x, new_start_y : new_start_y + size_y :]
        return result

    def __get_levels_ome_tif(self, tif_slide):
        levels = tif_slide.series[0].levels
        level_count = len(levels)
        level_dimensions = []
        level_downsamples = []

        for i, item in enumerate(levels):
            level_dimensions.append([item.keyframe.imagewidth, item.keyframe.imagelength])
            if i > 0:
                level_downsamples.append(level_dimensions[0][0] / item.keyframe.imagewidth)
            else:
                level_downsamples.append(1)

        original_levels = get_original_levels(level_count, level_dimensions, level_downsamples)
        return original_levels

    def __get_xml_namespace(self):
        m = re.match(r"\{.*\}", self.parsed_metadata.tag)
        return m.group(0) if m else ""

    def __get_channels_ome_tif(self):
        namespace = self.__get_xml_namespace()
        xml_channels = (
            self.parsed_metadata.find(f"{ namespace }Image")
            .find(f"{ namespace }Pixels")
            .findall(f"{ namespace }Channel")
        )
        channels = []
        for i, xmlc in enumerate(xml_channels):
            color_int = convert_int_to_rgba_array(int(xmlc.get("Color")))
            temp_channel = SlideChannel(
                id=i,
                name=xmlc.get("Name"),
                color=SlideColor(r=color_int[0], g=color_int[1], b=color_int[2], a=color_int[3]),
            )
            channels.append(temp_channel)
        return channels

    def __get_pixel_size_ome_tif(self):
        namespace = self.__get_xml_namespace()
        pixel_unit_x = (
            self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").get("PhysicalSizeXUnit")
        )
        pixel_unit_y = (
            self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").get("PhysicalSizeYUnit")
        )
        if pixel_unit_x != pixel_unit_y:
            raise HTTPException(
                status_code=500,
                detail="Different pixel size unit in x- and y-direction not supported.",
            )
        pixel_size_x = (
            self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").get("PhysicalSizeX")
        )
        pixel_size_y = (
            self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").get("PhysicalSizeY")
        )
        if pixel_unit_x == "nm":
            return SlidePixelSizeNm(x=float(pixel_size_x), y=float(pixel_size_y))
        elif pixel_unit_x == "µm":
            x = float(pixel_size_x) * 1000
            y = float(pixel_size_y) * 1000
            return SlidePixelSizeNm(x=x, y=y)
        elif pixel_unit_x == "cm":
            x = float(pixel_size_x) * 1e6
            y = float(pixel_size_y) * 1e6
            return SlidePixelSizeNm(x=x, y=y)
        else:
            raise HTTPException(status_code=500, detail=f"Invalid pixel size unit ({pixel_unit_x})")

    def __get_slide_info_ome_tif(self):
        serie = self.tif_slide.series[0]
        channels = self.__get_channels_ome_tif()
        pixel_size = self.__get_pixel_size_ome_tif()
        levels = self.__get_levels_ome_tif(self.tif_slide)
        try:
            slide_info = SlideInfo(
                id="",
                channels=channels,
                channel_depth=serie.keyframe.bitspersample,
                extent=SlideExtent(
                    x=serie.keyframe.imagewidth,
                    y=serie.keyframe.imagelength,
                    z=serie.keyframe.imagedepth,
                ),
                pixel_size_nm=pixel_size,
                tile_extent=SlideExtent(
                    x=serie.keyframe.tilewidth,
                    y=serie.keyframe.tilelength,
                    z=serie.keyframe.tiledepth,
                ),
                num_levels=len(levels),
                levels=levels,
                format="ome-tiff",
            )
            return slide_info
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Failed to gather slide infos. [{e}]")
