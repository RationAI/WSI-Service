import json
import os.path as os
import re
import xml.etree.ElementTree as xml

import numpy as np
import tifffile
from fastapi import HTTPException
from skimage import transform, util

from wsi_service.models.slide import Channel, Extent, Level, PixelSizeNm, SlideInfo
from wsi_service.settings import Settings
from wsi_service.slide import Slide
from wsi_service.slide_utils import (
    check_generated_levels_for_originals,
    get_generated_levels,
    get_original_levels,
)


class OmeTiffSlide(Slide):
    supported_file_types = ["tif", "tiff", "ome.tif", "ome.tiff", ".ome.tf2", ".ome.tf8", ".ome.btf"]
    format_kinds = ["OME"]  # what else is supported?
    loader_name = "OmeTiffSlide"

    def __init__(self, filepath, slide_id):
        try:
            self.tif_slide = tifffile.TiffFile(filepath)
            if self.tif_slide.series[0].kind not in self.format_kinds:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unsupported file format ({self.tif_slide.series[0].kind})",
                )
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to load tiff file. [{e}]",
            )
        # read pixel sizes from xml image description
        self.ome_metadata = self.tif_slide.ome_metadata
        self.parsed_metadata = xml.fromstring(self.ome_metadata)
        # pixel_size = self.get_pixel_size(self.parsed_metadata[0][0])
        self.slide_info = self.__get_slide_info_ome_tif(slide_id, self.parsed_metadata)

    def close(self):
        self.tif_slide.close()

    def get_info(self):
        return self.slide_info

    def get_best_original_level(self, level):
        for i in range(level - 1, 0, -1):
            if not self.slide_info.levels[i].generated:
                return self.slide_info.levels[i]
        return None

    def get_tif_level_for_slide_level(self, slide_level):
        for level in self.tif_slide.series[0].levels:
            if level.shape[1] == slide_level.extent.y:
                return level

    def get_region(self, level, start_x, start_y, size_x, size_y):
        settings = Settings()
        try:
            level_slide = self.slide_info.levels[level]
        except IndexError:
            raise HTTPException(
                status_code=422,
                detail=f"""The requested pyramid level is not available. 
                    The coarsest available level is {len(self.slide_info.levels) - 1}.""",
            )

        result_array = []
        if level_slide.generated:
            base_level = self.get_best_original_level(level)
            if base_level == None:
                raise HTTPException(
                    status_code=422,
                    detail=f"No appropriate base level for generagted level {level} found",
                )
            base_size = (
                round(size_x * (level_slide.downsample_factor / base_level.downsample_factor)),
                round(size_y * (level_slide.downsample_factor / base_level.downsample_factor)),
            )
            if base_size[0] * base_size[1] > settings.max_returned_region_size:
                raise HTTPException(
                    status_code=403,
                    detail=f"""Requested image region is too large. Maximum number of pixels is set to 
                        {settings.max_returned_region_size}, your request is for {base_size[0] * base_size[1]} pixels.""",
                )
            level_0_location = (
                (int)(start_x * base_level.downsample_factor),
                (int)(start_y * base_level.downsample_factor),
            )
            tif_level = self.get_tif_level_for_slide_level(base_level)
            for page in tif_level.pages:
                temp_channel = self.__read_region_of_page(
                    page, level_0_location[0], level_0_location[1], base_size[0], base_size[1]
                )
                # resize for requested image level
                resized = util.img_as_uint(
                    transform.resize(temp_channel, (temp_channel.shape[0], size_x, size_y, temp_channel.shape[3]))
                )
                result_array.append(resized)
        else:
            tif_level = self.get_tif_level_for_slide_level(level_slide)
            for page in tif_level.pages:
                temp_channel = self.__read_region_of_page(page, start_x, start_y, size_x, size_y)
                result_array.append(temp_channel)

        result = np.concatenate(result_array, axis=0)[:, :, :, 0]

        # todo: manipulate metadata
        # self.manipulate_metadata("CYZ", "0.325", "0.325", result.shape[1], result.shape[2])

        # debug
        """temp_dir = os.expanduser("~")
        tifffile.imwrite(
            temp_dir + "/Documents/test.ome.tif",
            result,
            photometric="minisblack",
            planarconfig="separate",
            description=self.ome_metadata,
        )"""

        return result, None  # self.ome_metadata

    def get_thumbnail(self, max_x, max_y):
        raise (NotImplementedError)

    def _get_associated_image(self, associated_image_name):
        raise (NotImplementedError)

    def get_label(self):
        raise (NotImplementedError)

    def get_macro(self):
        raise (NotImplementedError)

    def get_tile(self, level, tile_x, tile_y):
        # todo: implement extracting of tile without de/encoding of tile data
        return self.get_region(
            level,
            tile_x * self.slide_info.tile_extent.x,
            tile_y * self.slide_info.tile_extent.y,
            self.slide_info.tile_extent.x,
            self.slide_info.tile_extent.y,
        )

    ## private members

    def __read_region_of_page(self, page, start_x, start_y, size_x, size_y):
        page_frame = page.keyframe
        if not page_frame.is_tiled:
            raise HTTPException(
                status_code=422,
                detail="Tiff page is not tiled",
            )

        image_width, image_height = page_frame.imagewidth, page_frame.imagelength
        if (
            size_x < 1
            or size_y < 1
            or start_x < 0
            or start_y < 0
            or (start_x + size_x > image_width)
            or (start_y + size_y > image_height)
        ):
            raise HTTPException(
                status_code=422,
                detail=f"Requested image region exceeds bounds of base level (w={image_width}, h={image_height})",
            )

        tile_width, tile_height = page_frame.tilewidth, page_frame.tilelength
        end_x, end_y = start_x + size_x, start_y + size_y

        start_tile_x0, start_tile_y0 = start_x // tile_height, start_y // tile_width
        end_tile_xn, end_tile_yn = np.ceil([end_x / tile_height, end_y / tile_width]).astype(int)

        tile_per_line = int(np.ceil(image_width / tile_width))

        # initialize array with size of all relevant tiles
        out = np.empty(
            (
                page_frame.imagedepth,
                (end_tile_xn - start_tile_x0) * tile_height,
                (end_tile_yn - start_tile_y0) * tile_width,
                page_frame.samplesperpixel,
            ),
            dtype=page_frame.dtype,
        )

        fh = page.parent.filehandle

        if fh == None:
            raise HTTPException(status_code=422, detail="Could not read from tiff file. File handle is null")

        jpegtables = page.jpegtables
        if jpegtables is not None:
            jpegtables = jpegtables.value

        # iterate through tiles starting at the top left to the bottom right
        for i in range(start_tile_x0, end_tile_xn):
            for j in range(start_tile_y0, end_tile_yn):
                index = int(i * tile_per_line + j)

                offset = page.dataoffsets[index]
                bytecount = page.databytecounts[index]

                # search to tile offset and read image tile
                fh.seek(offset)
                if fh.tell() != offset:
                    raise HTTPException(
                        status_code=422,
                        detail="Failed reading to tile offset",
                    )
                data = fh.read(bytecount)
                tile, _, _ = page.decode(data, index, jpegtables)

                # insert tile in temporary output array
                tile_position_i = (i - start_tile_x0) * tile_height
                tile_position_j = (j - start_tile_y0) * tile_width
                out[
                    :, tile_position_i : tile_position_i + tile_height, tile_position_j : tile_position_j + tile_width :
                ] = tile

        # determine the new start positions of our region
        new_start_x = start_x - start_tile_x0 * tile_height
        nex_start_y = start_y - start_tile_y0 * tile_width

        # restrict the output array to the requested region
        result = out[:, new_start_x : new_start_x + size_x, nex_start_y : nex_start_y + size_y :]
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
        generated_levels = get_generated_levels(level_dimensions[0], original_levels[-1])
        check_generated_levels_for_originals(original_levels, generated_levels)
        return generated_levels

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
            temp_channel = Channel(id=i, name=xmlc.get("Name"), color_int=int(xmlc.get("Color")))
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
                status_code=422,
                detail="Different pixel size unit in x- and y-direction not supported.",
            )
        pixel_size_x = (
            self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").get("PhysicalSizeX")
        )
        pixel_size_y = (
            self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").get("PhysicalSizeY")
        )
        if pixel_unit_x == "nm":
            return PixelSizeNm(x=float(pixel_size_x), y=float(pixel_size_y))
        elif pixel_unit_x == "µm":
            x = float(pixel_size_x) * 1000
            y = float(pixel_size_y) * 1000
            return PixelSizeNm(x=x, y=y)
        elif pixel_unit_x == "cm":
            x = float(pixel_size_x) * 1e6
            y = float(pixel_size_y) * 1e6
            return PixelSizeNm(x=x, y=y)
        else:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid pixel size unit ({pixel_unit_x})",
            )

    def __get_slide_info_ome_tif(self, slide_id, parsed_metadata):
        serie = self.tif_slide.series[0]
        channels = self.__get_channels_ome_tif()
        pixel_size = self.__get_pixel_size_ome_tif()
        levels = self.__get_levels_ome_tif(self.tif_slide)
        try:
            slide_info = SlideInfo(
                id=slide_id,
                channels=channels,
                channel_depth=serie.keyframe.bitspersample,
                extent=Extent(x=serie.keyframe.imagewidth, y=serie.keyframe.imagelength, z=serie.keyframe.imagedepth),
                pixel_size_nm=pixel_size,
                tile_extent=Extent(x=serie.keyframe.tilewidth, y=serie.keyframe.tilelength, z=serie.keyframe.tiledepth),
                num_levels=len(levels),
                levels=levels,
            )
            return slide_info
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to gather slide infos. [{e}]",
            )

    def __manipulate_metadata(self, dimOrder, p_size_x, p_size_y, size_x, size_y):
        namespace = self.__get_xml_namespace()
        self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").set("DimensionOrder", dimOrder)
        self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").set("SizeX", str(size_x))
        self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").set("SizeY", str(size_y))
        self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").set(
            "PhysicalSizeX", str(p_size_x)
        )
        self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").set(
            "PhysicalSizeY", str(p_size_y)
        )
        metadata = xml.tostring(self.parsed_metadata).decode("utf-8")
        # add xml decoding
        self.ome_metadata = f'<?xml version="1.0" encoding="UTF-8"?>\n{metadata}'
