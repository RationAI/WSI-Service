import json
import os.path as os
import re
import xml.etree.ElementTree as xml

import numpy as np
import tifffile
from fastapi import HTTPException
from skimage import transform, util

from wsi_service.models.slide import Extent, Level, PixelSizeNm, SlideInfo
from wsi_service.settings import Settings
from wsi_service.slide import Slide
from wsi_service.slide_utils import get_slide_info_ome_tif


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
        self.parsed_metadata = xml.fromstring(self.ome_metadata)  # omexmlClass.OMEXML(self.ome_metadata)
        pixel_size = self.get_pixel_size(self.parsed_metadata[0][0])
        self.slide_info = get_slide_info_ome_tif(self.tif_slide, slide_id, pixel_size)

    def get_xml_namespace(self, element):
        m = re.match(r"\{.*\}", element.tag)
        return m.group(0) if m else ""

    def manipulate_metadata(self, dimOrder, p_size_x, p_size_y, size_x, size_y):
        namespace = self.get_xml_namespace(self.parsed_metadata)
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

    def get_pixel_size(self, xml_imagedata):
        # z-direction?
        pixel_unit_x = xml_imagedata.attrib["PhysicalSizeXUnit"]
        pixel_unit_y = xml_imagedata.attrib["PhysicalSizeYUnit"]
        if pixel_unit_x != pixel_unit_y:
            raise HTTPException(
                status_code=422,
                detail="Different pixel size unit in x- and y-direction not supported.",
            )
        pixel_size_x = xml_imagedata.attrib["PhysicalSizeX"]
        pixel_size_y = xml_imagedata.attrib["PhysicalSizeY"]
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
                temp_channel = self.read_region_of_page(
                    page, level_0_location[0], level_0_location[1], base_size[0], base_size[1]
                )
                resized = util.img_as_uint(
                    transform.resize(temp_channel, (temp_channel.shape[0], size_x, size_y, temp_channel.shape[3]))
                )
                result_array.append(resized)
        else:
            tif_level = self.get_tif_level_for_slide_level(level_slide)
            for page in tif_level.pages:
                temp_channel = self.read_region_of_page(page, start_x, start_y, size_x, size_y)
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

    def read_region_of_page(self, page, start_x, start_y, size_x, size_y):
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
                detail="Requested image region is not valid",
            )
        tile_width, tile_height = page_frame.tilewidth, page_frame.tilelength
        end_x, end_y = start_x + size_x, start_y + size_y

        start_tile_x0, start_tile_y0 = start_x // tile_width, start_y // tile_height
        end_tile_xn, end_tile_yn = np.ceil([end_x / tile_width, end_y / tile_height]).astype(int)

        tile_per_line = int(np.ceil(image_width / tile_width))
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

        jpegtables = page.jpegtables
        if jpegtables is not None:
            jpegtables = jpegtables.value

        for i in range(start_tile_x0, end_tile_xn):
            for j in range(start_tile_y0, end_tile_yn):
                index = int(i * tile_per_line + j)

                offset = page.dataoffsets[index]
                bytecount = page.databytecounts[index]

                fh.seek(offset)
                data = fh.read(bytecount)
                tile, indices, shape = page.decode(data, index, jpegtables)

                tile_position_i = (i - start_tile_x0) * tile_height
                tile_position_j = (j - start_tile_y0) * tile_width
                out[
                    :, tile_position_i : tile_position_i + tile_height, tile_position_j : tile_position_j + tile_width :
                ] = tile

        im_i0 = start_x - start_tile_x0 * tile_height
        im_j0 = start_y - start_tile_y0 * tile_width

        result = out[:, im_i0 : im_i0 + size_x, im_j0 : im_j0 + size_y :]
        return result

    def get_thumbnail(self, max_x, max_y):
        raise (NotImplementedError)

    def _get_associated_image(self, associated_image_name):
        raise (NotImplementedError)

    def get_label(self):
        raise (NotImplementedError)

    def get_macro(self):
        raise (NotImplementedError)

    def get_tile(self, level, tile_x, tile_y):
        return self.get_region(
            level,
            tile_x * self.slide_info.tile_extent.x,
            tile_y * self.slide_info.tile_extent.y,
            self.slide_info.tile_extent.x,
            self.slide_info.tile_extent.y,
        )
