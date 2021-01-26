from io import BytesIO

import tifffile
from fastapi import HTTPException
from starlette.responses import StreamingResponse

supported_image_formats = {
    "bmp": "image/bmp",
    "gif": "image/gif",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "tiff": "image/tiff",
    "ome.tif": "image/ome.tif",
}

supported_image_formats_for_ome_tif = {
    "tiff": "image/tiff",
    "ome.tif": "image/ome.tif",
}

alternative_spellings = {
    "jpg": "jpeg",
    "tif": "tiff",
    "ome.tiff": "ome.tif",
    "ome.tf2": "ome.tif",
    "ome.tf8": "ome.tif",
    "ome.btf": "ome.tif",
}


def make_image_response(pil_image, image_format, image_quality):
    if image_format in alternative_spellings:
        image_format = alternative_spellings[image_format]

    if image_format not in supported_image_formats:
        raise HTTPException(status_code=400, detail="Provided image format parameter not supported")
    mem = BytesIO()
    if image_format == "png":
        pil_image.save(mem, format=image_format, optimize=(image_quality > 0))
    else:
        pil_image.save(mem, format=image_format, quality=image_quality)
    mem.seek(0)
    return StreamingResponse(mem, media_type=supported_image_formats[image_format])


def make_tif_response(narray, metadata, image_format, image_quality):
    if image_format in alternative_spellings:
        image_format = alternative_spellings[image_format]

    if image_format not in supported_image_formats_for_ome_tif:
        raise HTTPException(status_code=400, detail="Provided image format parameter not supported for OME tiff")
    mem = BytesIO()
    # zlib compression ranges from 0-9
    compression_level = (int)((image_quality / 100) * (-9) + 9)
    if metadata == None:
        tifffile.imwrite(mem, narray, photometric="minisblack", planarconfig="separate", compress=compression_level)
    else:
        tifffile.imwrite(
            mem,
            narray,
            photometric="minisblack",
            planarconfig="separate",
            compress=compression_level,
            description=metadata,
        )
    mem.seek(0)
    return StreamingResponse(mem, media_type=supported_image_formats[image_format])


def validate_image_request(image_format, image_quality):
    if image_format not in supported_image_formats and image_format not in alternative_spellings:
        raise HTTPException(status_code=400, detail="Provided image format parameter not supported")
    if image_quality < 0 or image_quality > 100:
        raise HTTPException(status_code=400, detail="Provided image quality parameter not supported")
