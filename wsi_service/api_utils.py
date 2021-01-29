from io import BytesIO

import numpy as np
import tifffile
from fastapi import HTTPException
from PIL import Image
from starlette.responses import StreamingResponse

from wsi_service.image_utils import (
    convert_narray_to_pil_image,
    convert_rgb_image_for_channels,
    save_rgb_image,
)

supported_image_formats = {
    "bmp": "image/bmp",
    "gif": "image/gif",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "tiff": "image/tiff",
}

alternative_spellings = {
    "jpg": "jpeg",
    "tif": "tiff",
}


def get_image_region(slide, level, image_channels, start_x, start_y, size_x, size_y):
    image_tile = slide.get_region(level, start_x, start_y, size_x, size_y)
    if isinstance(image_tile, Image.Image):
        # pillow image
        if image_channels == None:
            return image_tile
        else:
            return convert_rgb_image_for_channels(image_tile, image_channels)
    elif isinstance(image_tile, (np.ndarray, np.generic)):
        # numpy array
        if image_channels == None:
            rgb_image = convert_narray_to_pil_image(image_tile)
            return rgb_image
        else:
            # for i in image_channels:
            #    image_tile[i::0] = 0
            rgb_image = convert_narray_to_pil_image(image_tile)
            return rgb_image
    else:
        raise HTTPException(status_code=400, detail="Failed to read region in an apropriate internal representation.")


def get_image_region_raw(slide, level, image_channels, start_x, start_y, size_x, size_y):
    image_tile = slide.get_region(level, start_x, start_y, size_x, size_y)
    if isinstance(image_tile, Image.Image):
        # pillow image
        narray = np.asarray(image_tile)
        narray = np.ascontiguousarray(narray.transpose(2, 0, 1))
        return narray
    elif isinstance(image_tile, (np.ndarray, np.generic)):
        # numpy array
        if image_channels == None:
            return image_tile
        else:
            separate_channels = np.vsplit(image_tile, image_tile.shape[0])
            temp_array = []
            for i in image_channels:
                temp_array.append(separate_channels[i])
            result = np.concatenate(temp_array, axis=0)
            return result
    else:
        raise HTTPException(status_code=400, detail="Failed to read region in an apropriate internal representation.")


def make_image_response(pil_image, image_format, image_quality):
    if image_format in alternative_spellings:
        image_format = alternative_spellings[image_format]

    if image_format not in supported_image_formats:
        raise HTTPException(status_code=400, detail="Provided image format parameter not supported")

    mem = save_rgb_image(pil_image, image_format, image_quality)
    return StreamingResponse(mem, media_type=supported_image_formats[image_format])


def make_tif_response(narray, image_format, image_quality):
    if image_format in alternative_spellings:
        image_format = alternative_spellings[image_format]

    if image_format not in supported_image_formats:
        raise HTTPException(status_code=400, detail="Provided image format parameter not supported for OME tiff")

    mem = BytesIO()
    if image_quality == 100:
        compression = "NONE"
    else:
        # if tiff is requested with compression, we use deflate
        # todo: check if this is working?
        compression = "DEFLATE"
    tifffile.imwrite(mem, narray, photometric="minisblack", planarconfig="separate", compression=compression)
    mem.seek(0)

    return StreamingResponse(mem, media_type=supported_image_formats[image_format])


def validate_image_request(image_format, image_quality):
    if image_format not in supported_image_formats and image_format not in alternative_spellings:
        raise HTTPException(status_code=400, detail="Provided image format parameter not supported")
    if image_quality < 0 or image_quality > 100:
        raise HTTPException(status_code=400, detail="Provided image quality parameter not supported")
