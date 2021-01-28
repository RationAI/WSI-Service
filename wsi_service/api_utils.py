from io import BytesIO

import numpy as np
import tifffile
from fastapi import HTTPException
from PIL import Image
from starlette.responses import StreamingResponse

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
            # todo: color spaces of channel!
            rgb_image = convert_narray_to_pil_image(image_tile)
            return rgb_image
        else:
            # for i in image_channels:
            #    image_tile[i::0] = 0
            rgb_image = convert_narray_to_pil_image(image_tile)
            return rgb_image
    else:
        raise HTTPException(status_code=404, detail="Failed to read region in an apropriate internal representation.")


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
            return None
    else:
        raise HTTPException(status_code=404, detail="Failed to read region in an apropriate internal representation.")


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
        compression_level = "NONE"
    else:
        # zlib compression ranges from 0-9
        compression_level = ("DEFLATE", (int)((image_quality / 100) * (-9) + 9))
    tifffile.imwrite(mem, narray, photometric="minisblack", planarconfig="separate", compression=compression_level)
    mem.seek(0)

    return StreamingResponse(mem, media_type=supported_image_formats[image_format])


def validate_image_request(image_format, image_quality):
    if image_format not in supported_image_formats and image_format not in alternative_spellings:
        raise HTTPException(status_code=400, detail="Provided image format parameter not supported")
    if image_quality < 0 or image_quality > 100:
        raise HTTPException(status_code=400, detail="Provided image quality parameter not supported")


def convert_narray_uint16_to_uint8(array, lower=None, upper=None):
    if lower is not None and not (0 <= lower < 2 ** 16):
        raise ValueError("lower bound must be between 0 and 2**16")
    if upper is not None and not (0 <= upper < 2 ** 16):
        raise ValueError("upper bound must be between 0 and 2**16")
    if lower is None:
        lower = np.min(array)
    if upper is None:
        upper = np.max(array)

    scale = 255 / (upper - lower)
    temp_array = (array - upper) * scale + lower
    return (temp_array.clip(lower, upper) + 0.5).astype(np.uint8)


def save_rgb_image(pil_image, image_format, image_quality):
    mem = BytesIO()
    if image_format == "png":
        pil_image.save(mem, format=image_format, optimize=(image_quality > 0))
    else:
        pil_image.save(mem, format=image_format, quality=image_quality)
    mem.seek(0)
    return mem


def convert_rgb_image_for_channels(image_tile, image_channel):
    r = 1 if 0 in image_channel else 0
    g = 1 if 1 in image_channel else 0
    b = 1 if 2 in image_channel else 0
    conv_matrix = (r, 0, 0, 0, 0, g, 0, 0, 0, 0, b, 0)
    converted_image = image_tile.convert("RGB", conv_matrix)
    return converted_image


def convert_narray_to_pil_image(narray):
    narray_uint8 = convert_narray_uint16_to_uint8(narray)
    # we need to transpose the array here to make it readable for pillow (width, height, channel)
    narray_uint8 = np.ascontiguousarray(narray_uint8.transpose(1, 2, 0))
    pil_image = Image.fromarray(narray_uint8)
    return pil_image
