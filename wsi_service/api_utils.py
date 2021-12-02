import re
from io import BytesIO

import numpy as np
import tifffile
from fastapi import HTTPException
from PIL import Image
from starlette.responses import Response

from wsi_service.image_utils import (
    convert_narray_to_pil_image,
    convert_rgb_image_for_channels,
    get_requested_channels_as_array,
    get_requested_channels_as_rgb_array,
    save_rgb_image,
)
from wsi_service.singletons import settings

supported_image_formats = {
    "bmp": "image/bmp",
    "gif": "image/gif",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "tiff": "image/tiff",
}

alternative_spellings = {"jpg": "jpeg", "tif": "tiff"}


def process_image_region(slide, image_tile, image_channels):
    if isinstance(image_tile, Image.Image):
        # pillow image
        if image_channels == None:
            return image_tile
        else:
            return convert_rgb_image_for_channels(image_tile, image_channels)
    elif isinstance(image_tile, (np.ndarray, np.generic)):
        # numpy array
        if image_channels == None:
            # workaround for now: we return first three channels as rgb
            result = get_requested_channels_as_rgb_array(image_tile, None, slide)
            rgb_image = convert_narray_to_pil_image(result)
            return rgb_image
        else:
            result = get_requested_channels_as_rgb_array(image_tile, image_channels, slide)
            mode = "L" if len(image_channels) == 1 else "RGB"
            rgb_image = convert_narray_to_pil_image(result, np.min(result), np.max(result), mode=mode)
            return rgb_image
    else:
        raise HTTPException(status_code=400, detail="Failed to read region in an apropriate internal representation.")


def process_image_region_raw(image_tile, image_channels):
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
            result = get_requested_channels_as_array(image_tile, image_channels)
            return result
    else:
        raise HTTPException(status_code=400, detail="Failed to read region in an apropriate internal representation.")


def make_response(slide, image_region, image_format, image_quality, image_channels=None):
    if image_format == "tiff":
        # return raw image region as tiff
        narray = process_image_region_raw(image_region, image_channels)
        return make_tif_response(narray, image_format, image_quality)
    else:
        # return image region
        img = process_image_region(slide, image_region, image_channels)
        return make_image_response(img, image_format, image_quality)


def make_image_response(pil_image, image_format, image_quality):
    if image_format in alternative_spellings:
        image_format = alternative_spellings[image_format]

    if image_format not in supported_image_formats:
        raise HTTPException(status_code=400, detail="Provided image format parameter not supported")

    mem = save_rgb_image(pil_image, image_format, image_quality)
    return Response(mem.getvalue(), media_type=supported_image_formats[image_format])


def make_tif_response(narray, image_format, image_quality):
    if image_format in alternative_spellings:
        image_format = alternative_spellings[image_format]

    if image_format not in supported_image_formats:
        raise HTTPException(status_code=400, detail="Provided image format parameter not supported for OME tiff")

    mem = BytesIO()
    if image_quality == 0:
        # lossy comprssion with jpeg
        compression = "JPEG"
    else:
        # by default we use deflate
        compression = "DEFLATE"
    tifffile.imwrite(mem, narray, photometric="minisblack", planarconfig="separate", compression=compression)
    mem.seek(0)

    return Response(mem.getvalue(), media_type=supported_image_formats[image_format])


def validate_image_request(image_format, image_quality):
    if image_format not in supported_image_formats and image_format not in alternative_spellings:
        raise HTTPException(status_code=400, detail="Provided image format parameter not supported")
    if image_quality < 0 or image_quality > 100:
        raise HTTPException(status_code=400, detail="Provided image quality parameter not supported")


def validate_hex_color_string(padding_color):
    if padding_color:
        match = re.search(r"^#(?:[0-9a-fA-F]{3}){1,2}$", padding_color)
        if match:
            stripped_padding_color = padding_color.lstrip("#")
            int_padding_color = tuple(int(stripped_padding_color[i : i + 2], 16) for i in (0, 2, 4))
            return int_padding_color
    return settings.padding_color


def validate_image_channels(slide, image_channels):
    if image_channels is None:
        return
    for i in image_channels:
        if i >= len(slide.slide_info.channels):
            raise HTTPException(
                status_code=400,
                detail=f"Selected image channel excceds channel bounds (selected: {i} max: {len(slide.slide_info.channels)-1})",
            )
    if len(image_channels) != len(set(image_channels)):
        raise HTTPException(status_code=400, detail="No duplicates allowed in channels")
