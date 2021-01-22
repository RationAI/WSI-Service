import json
import os.path as os
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
        parsed_metadata = xml.fromstring(self.ome_metadata)
        pixel_size = self.get_pixel_size(parsed_metadata[0][0])
        self.slide_info = get_slide_info_ome_tif(self.tif_slide, slide_id, pixel_size)

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

    def get_best_level_for_downsample(self, downsample_factor):
        if downsample_factor < self.slide_info.levels[0].downsample_factor:
            return 0
        for i, level in enumerate(self.slide_info.levels):
            if downsample_factor < level.downsample_factor:
                return i - 1
        return len(self.slide_info.levels) - 1

    def get_region(self, level, start_x, start_y, size_x, size_y):
        settings = Settings()
        try:
            downsample_factor = int(self.slide_info.levels[level].downsample_factor)
        except IndexError:
            raise HTTPException(
                status_code=422,
                detail=f"""The requested pyramid level is not available. 
                    The coarsest available level is {len(self.slide_info.levels) - 1}.""",
            )
        base_level = self.get_best_level_for_downsample(downsample_factor)
        # todo get level for downsample factor
        level = self.tif_slide.series[0].levels[base_level]
        result_array = []
        for page in level.pages:
            temp_channel = self.read_region_of_page(page, start_x, start_y, size_x, size_y)
            # todo: calculate resize factor
            # resized = util.img_as_uint(transform.resize(temp_channel, (1, 512, 512, 1)))
            resized = temp_channel
            result_array.append(resized)
        result = np.concatenate(result_array, axis=0)

        metadata = json.dumps(self.ome_metadata)
        temp_dir = os.expanduser("~")
        tifffile.imwrite(temp_dir + "/Documents/test.ome.tif", result, photometric="minisblack", description=metadata)
        return result, metadata

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
        # switch height and width?
        tile_i0, tile_j0 = start_x // tile_width, start_y // tile_height
        tile_i1, tile_j1 = np.ceil([end_x / tile_width, end_y / tile_height]).astype(int)

        tile_per_line = int(np.ceil(image_width / tile_width))
        out = np.empty(
            (
                page_frame.imagedepth,
                (tile_i1 - tile_i0) * tile_height,
                (tile_j1 - tile_j0) * tile_width,
                page_frame.samplesperpixel,
            ),
            dtype=page_frame.dtype,
        )

        fh = page.parent.filehandle

        jpegtables = page.jpegtables
        if jpegtables is not None:
            jpegtables = jpegtables.value

        for i in range(tile_i0, tile_i1):
            for j in range(tile_j0, tile_j1):
                index = int(i * tile_per_line + j)

                offset = page.dataoffsets[index]
                bytecount = page.databytecounts[index]

                fh.seek(offset)
                data = fh.read(bytecount)
                tile, indices, shape = page.decode(data, index, jpegtables)

                im_i = (i - tile_i0) * tile_height
                im_j = (j - tile_j0) * tile_width
                out[:, im_i : im_i + tile_height, im_j : im_j + tile_width, :] = tile

        im_i0 = start_x - tile_i0 * tile_height
        im_j0 = start_y - tile_j0 * tile_width

        result = out[:, im_i0 : im_i0 + size_x, im_j0 : im_j0 + size_y, :]
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
