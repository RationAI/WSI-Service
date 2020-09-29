from io import BytesIO

from starlette.responses import StreamingResponse
from fastapi import HTTPException


supported_image_formats = {
    'bmp': 'image/bmp',
    'gif': 'image/gif',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'tiff': 'image/tiff'
}

alternative_spellings = {
    'jpg': 'jpeg',
    'tif': 'tiff'
}


def make_image_response(pil_image, image_format,
                        image_quality, resize_x=None, resize_y=None):
    if image_format in alternative_spellings:
        image_format = alternative_spellings[image_format]

    if image_format in supported_image_formats:
        io = BytesIO()
        pil_image.save(io, format=image_format, quality=image_quality)
        io.seek(0)
        return StreamingResponse(
            io, media_type=supported_image_formats[image_format])
    else:
        raise HTTPException(
            status_code=400,
            detail="Provided image format parameter not supported")


def validate_image_request(image_format, image_quality):
    if image_format not in supported_image_formats and
    image_format not in alternative_spellings:
        raise HTTPException(
            status_code=400,
            detail="Provided image format parameter not supported")
    if image_quality < 0 or image_quality > 100:
        raise HTTPException(
            status_code=400,
            detail="Provided image quality parameter not supported")
