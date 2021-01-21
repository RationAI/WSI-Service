import xml.etree.ElementTree as xml

import numpy as np
import tifffile
from fastapi import HTTPException

from wsi_service.models.slide import Extent, Level, PixelSizeNm, SlideInfo
from wsi_service.slide import Slide


class OmeTiffSlide(Slide):
    supported_file_types = ["tif", "tiff", "ome.tif", "ome.tiff", ".ome.tf2", ".ome.tf8", ".ome.btf"]
    format_kinds = ["OME"] # what else is supported?
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
        self.slide_info = self.get_ome_slide_info(slide_id)

    def get_ome_slide_info(self, slide_id):
        levels = self.tif_slide.series[0].levels
        num_levels = len(levels) # or is len(series[0].pages) better?
        ome_metadata = xml.fromstring(self.tif_slide.pages[0].tags["ImageDescription"].value)
        size_x = ome_metadata[0][0].attrib['SizeX']
        size_y = ome_metadata[0][0].attrib['SizeY']
        size_z = ome_metadata[0][0].attrib['SizeZ']
        return SlideInfo(
            id=slide_id,
            channel_count=float(ome_metadata[0][0].attrib['SizeC']),
            channel_depth=self.tif_slide.series[0].keyframe.bitspersample,
            extent=Extent(
                x=size_x, y=size_y, z=size_z
            ),
            pixel_size_nm=self.get_pixel_size(ome_metadata[0][0]),
            tile_extent=self.get_tile_extent(self.tif_slide.pages[0]),
            num_levels=num_levels,
            levels=self.get_slide_levels(self.tif_slide.pages),
        )
    
    def get_slide_levels(self, pages):
        print('pages')
        for page in pages:
            print(page.shape)
        return [Level(extent=Extent(x=0, y=0, z=0), downsample_factor=1, generated=True)]

    def get_tile_extent(self, first_page):
        print('file_extent')
        print(first_page.tags)
        return Extent(
                x=0, y=0, z=0
            )

    def get_pixel_size(self, xml_imagedata):
        # z-direction?
        pixel_unit_x = xml_imagedata.attrib['PhysicalSizeXUnit']
        pixel_unit_y = xml_imagedata.attrib['PhysicalSizeYUnit']
        if pixel_unit_x != pixel_unit_y:
            raise HTTPException(
                status_code=422,
                detail="Different pixel size unit in x- and y-direction not supported.",
            )
        pixel_size_x = xml_imagedata.attrib['PhysicalSizeX']
        pixel_size_y = xml_imagedata.attrib['PhysicalSizeY']
        if pixel_unit_x == 'nm':
            return PixelSizeNm(x=float(pixel_size_x), y=float(pixel_size_y))
        elif pixel_unit_x == 'µm':
            x = float(pixel_size_x) * 1000
            y = float(pixel_size_y) * 1000
            return PixelSizeNm(x=x, y=y)
        elif pixel_unit_x == 'cm':
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

    def get_region(self, level, start_x, start_y, size_x, size_y):
        if level >= len(self.tif_slide.series[0].levels):
            raise HTTPException(
                status_code=422,
                detail="Resolution level....",
            )

        level = self.tif_slide.series[0].levels[level]
        result_array = []
        for page in level.pages:
            temp_channel = self.read_region_of_page(page, start_x, start_y, size_x, size_y)
            result_array.append(temp_channel)
        result = np.concatenate(result_array, axis=-1)
        #tifffile.imwrite('test.tif', result)
        return result

    def read_region_of_page(self, page, start_x, start_y, size_x, size_y):
        page_frame = page.keyframe
        if not page_frame.is_tiled:
            raise HTTPException(
                status_code=422,
                detail="Tiff page is not tiled",
            )
        image_width, image_height = page_frame.imagewidth, page_frame.imagelength
        if size_x < 1 or size_y < 1 or start_x < 0 or start_y < 0 or (start_x + size_x > image_width) or (start_y + size_y > image_height):
            raise HTTPException(
                status_code=422,
                detail="Requested image region is not valid",
            )
        tile_width, tile_height = page_frame.tilewidth, page_frame.tilelength
        end_x, end_y = start_x + size_x, start_y + size_y

        tile_i0, tile_j0 = start_x // tile_height, start_y // tile_width
        tile_i1, tile_j1 = np.ceil([end_x / tile_height, end_y / tile_width]).astype(int)

        tile_per_line = int(np.ceil(image_width / tile_width))
        out = np.empty((page_frame.imagedepth,
                    (tile_i1 - tile_i0) * tile_height,
                    (tile_j1 - tile_j0) * tile_width,
                    page_frame.samplesperpixel), dtype=page_frame.dtype)
        
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
                out[:, im_i: im_i + tile_height, im_j: im_j + tile_width, :] = tile

        im_i0 = start_x - tile_i0 * tile_height
        im_j0 = start_y - tile_j0 * tile_width

        result = out[:, im_i0: im_i0 + size_x, im_j0: im_j0 + size_y, :]
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
        raise (NotImplementedError)
