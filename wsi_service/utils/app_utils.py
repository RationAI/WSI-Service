import glob
import re
import uuid
from io import BytesIO
import os
from pathlib import Path
import gzip

import numpy as np
import tifffile
from fastapi import HTTPException
from PIL import Image
from starlette.responses import Response

from wsi_service.custom_models.old_v3.storage import StorageAddress
from wsi_service.singletons import settings, logger
from wsi_service.utils.image_utils import (
    convert_narray_to_pil_image,
    convert_rgb_image_for_channels,
    get_requested_channels_as_array,
    get_requested_channels_as_rgb_array,
    save_rgb_image,
)

supported_image_formats = {
    "bmp": "image/bmp",
    "gif": "image/gif",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "tiff": "image/tiff",
}

alternative_spellings = {"jpg": "jpeg", "tif": "tiff"}


def process_image_region(slide, image_region, image_channels):
    if isinstance(image_region, Image.Image):
        # pillow image
        if image_channels is None:
            return image_region
        else:
            return convert_rgb_image_for_channels(image_region, image_channels)
    elif isinstance(image_region, (np.ndarray, np.generic)):
        # numpy array
        if image_channels is None:
            # workaround for now: we return first three channels as rgb
            result = get_requested_channels_as_rgb_array(image_region, None, slide)
            rgb_image = convert_narray_to_pil_image(result)
            return rgb_image
        else:
            result = get_requested_channels_as_rgb_array(image_region, image_channels, slide)
            mode = "L" if len(image_channels) == 1 else "RGB"
            rgb_image = convert_narray_to_pil_image(result, np.min(result), np.max(result), mode=mode)
            return rgb_image
    else:
        raise HTTPException(status_code=400, detail="Failed to read region in an appropriate internal representation.")


def process_image_region_raw(image_region, image_channels):
    if isinstance(image_region, Image.Image):
        # pillow image
        narray = np.asarray(image_region)
        narray = np.ascontiguousarray(narray.transpose(2, 0, 1))
        return narray
    elif isinstance(image_region, (np.ndarray, np.generic)):
        # numpy array
        if image_channels is None:
            return image_region
        else:
            result = get_requested_channels_as_array(image_region, image_channels)
            return result
    else:
        raise HTTPException(status_code=400, detail="Failed to read region in an apropriate internal representation.")


def make_response(slide, image_region, image_format, image_quality, image_channels=None):
    if image_format != "raw":
        if isinstance(image_region, bytes):
            if image_format == "jpeg":
                return Response(image_region, media_type=supported_image_formats[image_format])
            else:
                image_region = Image.open(BytesIO(image_region))
    else:
        buf = BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as f:
            f.write(image_region)
        compressed_data = buf.getvalue()
        return Response(
            content=compressed_data,
            media_type="application/octet-stream",
            headers={
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed_data)),
            }
        )

    if image_format == "tiff":
        # return raw image region as tiff
        narray = process_image_region_raw(image_region, image_channels)
        return make_tif_response(narray, image_format)
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


def make_tif_response(narray, image_format):
    if image_format in alternative_spellings:
        image_format = alternative_spellings[image_format]

    if image_format not in supported_image_formats:
        raise HTTPException(status_code=400, detail="Provided image format parameter not supported for OME tiff")

    mem = BytesIO()
    try:
        if narray.shape[0] == 1:
            tifffile.imwrite(mem, narray, photometric="minisblack", compression="DEFLATE")
        else:
            tifffile.imwrite(mem, narray, photometric="minisblack", planarconfig="separate", compression="DEFLATE")
    except Exception as ex:
        raise HTTPException(status_code=400, detail=f"Error writing tiff file: {ex}")
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


def validate_image_channels(slide_info, image_channels):
    if image_channels is None:
        return
    for i in image_channels:
        if i >= len(slide_info.channels):
            raise HTTPException(
                status_code=400,
                detail=f"""
                Selected image channel exceeds channel bounds
                (selected: {i} max: {len(slide_info.channels)-1})
                """,
            )
    if len(image_channels) != len(set(image_channels)):
        raise HTTPException(status_code=400, detail="No duplicates allowed in channels")


def validate_image_size(size_x, size_y):
    if size_x * size_y > settings.max_returned_region_size:
        raise HTTPException(
            status_code=422,
            detail=f"Requested region may not contain more than {settings.max_returned_region_size} pixels.",
        )


def validate_image_z(slide_info, z):
    if z > 0 and (slide_info.extent.z == 1 or slide_info.extent.z is None):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid ZStackQuery z={z}. The image does not support multiple z-layers.",
        )
    if z > 0 and z >= slide_info.extent.z:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid ZStackQuery z={z}. The image has only {slide_info.extent.z} z-layers.",
        )


def validate_image_level(slide_info, level):
    if level >= len(slide_info.levels):
        raise HTTPException(
            status_code=422,
            detail="The requested pyramid level is not available. "
            + f"The coarsest available level is {len(slide_info.levels) - 1}.",
        )


def local_mode_abs_file_path_to_relative(filepath: str, server_data_root: str):
    if not server_data_root.endswith("/"):
        server_data_root = server_data_root + "/"
    return filepath.replace(server_data_root, "")


def local_mode_collect_secondary_files_v3(main_address: str, storage_address_id: str, slide_id: str, relative_to: str):
    abspath = relpath = main_address
    if main_address.startswith(relative_to):
        relpath = abspath.replace(relative_to + "/", "")
    else:
        abspath = os.path.join(relative_to, relpath)

    logger.info(f"{abspath } { relpath }  { relative_to}")
    # Dicom
    if os.path.isdir(abspath):
        result = list(map(lambda f:
            StorageAddress(
                address=local_mode_abs_file_path_to_relative(f, relative_to),
                main_address=False,
                storage_address_id=str(uuid.uuid4()),
                slide_id=slide_id,
        ), glob.glob(os.path.join(abspath, "*.dcm"))))

    # MIRAX
    elif abspath.endswith(".mrxs"):
        path = Path(abspath)
        parent_folder = path.parent
        file_basename = path.stem

        additional_files = glob.glob(os.path.join(parent_folder, file_basename, "*"))
        result = [
            StorageAddress(
                address=local_mode_abs_file_path_to_relative(f, relative_to),
                main_address=False,
                storage_address_id=str(uuid.uuid4()),
                slide_id=slide_id)
            for f in additional_files
        ]

    # Other supported files are typically single file
    else:
        result = []

    result.append(StorageAddress(
        address=relpath,
        main_address=True,
        storage_address_id=storage_address_id,
        slide_id=slide_id,
    ))
    return result
