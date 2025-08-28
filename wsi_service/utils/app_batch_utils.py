from io import BytesIO

import zipfile
import tifffile
from fastapi import HTTPException
from PIL import Image
from starlette.responses import Response

from wsi_service.singletons import logger
from wsi_service.models.v3.slide import SlideInfo
from wsi_service.utils.image_utils import (
    save_rgb_image
)

from wsi_service.utils.app_utils import (
    process_image_region,
    process_image_region_raw,
    validate_image_level,
    validate_image_channels,
    validate_image_z,
    supported_image_formats,
    alternative_spellings
)


async def safe_get_slide(slide_manager, path, plugin):
    try:
        return await slide_manager.get_slide(path, plugin=plugin)
    except Exception as e:
        logger.error(e)
        return None  # todo consider keeping the error message


async def safe_get_slide_for_query(slide_manager, path, plugin):
    try:
        return await slide_manager.get_slide_info(path, slide_info_model=SlideInfo, plugin=plugin)
    except Exception as e:
        return {'detail': getattr(e, 'message', repr(e))}


async def safe_get_slide_info(slide):
    if slide is None:
        return None
    try:
        return await slide.get_info()
    except Exception as e:
        logger.error(e)
        return None  # todo consider keeping the error message


async def safe_get_slide_icc_profile(slide):
    if slide is None:
        return None
    try:
        return await slide.get_icc_profile()
    except Exception as e:
        logger.error(e)
        return None  # todo consider keeping the error message


def batch_safe_make_response(slides, image_regions, image_format, image_quality, image_channels=None):
    # Create a ZipFile and add the NumPy array as an entry named 't1'
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', compression=zipfile.ZIP_STORED) as zip:
        for i in range(len(slides)):
            image_region = image_regions[i]
            slide = slides[i]

            if image_format != "raw":
                if isinstance(image_region, bytes):
                    if image_format == "jpeg":
                        zip.writestr(f't{i + 1}.jpeg', image_region)
                        continue
                    else:
                        image_region = Image.open(BytesIO(image_region))
            else:
                zip.writestr(f't{i + 1}.raw', image_region)

            if image_format == "tiff":
                mem = BytesIO()
                try:
                    # return raw image region as tiff
                    narray = process_image_region_raw(image_region, image_channels)
                    if image_format in alternative_spellings:
                        image_format = alternative_spellings[image_format]

                    if image_format not in supported_image_formats:
                        raise HTTPException(status_code=400,
                                            detail="Provided image format parameter not supported for OME tiff")
                    if narray.shape[0] == 1:
                        tifffile.imwrite(mem, narray, photometric="minisblack", compression="DEFLATE")
                    else:
                        tifffile.imwrite(mem, narray, photometric="minisblack", planarconfig="separate",
                                         compression="DEFLATE")
                    mem.seek(0)
                    zip.writestr(f't{i + 1}.{image_format}', mem.getvalue())
                except Exception as ex:
                    # just indicate error --> empty archive
                    zip.writestr(f't{i + 1}.err', getattr(ex, 'message', repr(ex)))
            else:
                try:
                    # return image region
                    img = process_image_region(slide, image_region, image_channels)
                    if image_format in alternative_spellings:
                        image_format = alternative_spellings[image_format]

                    if image_format not in supported_image_formats:
                        raise HTTPException(status_code=400, detail="Provided image format parameter not supported")

                    mem = save_rgb_image(img, image_format, image_quality)
                    zip.writestr(f't{i + 1}.{image_format}', mem.getvalue())
                except Exception as ex:
                    # just indicate error --> empty archive
                    zip.writestr(f't{i + 1}.err', getattr(ex, 'message', repr(ex)))
    return Response(zip_buffer.getvalue(), media_type="application/zip")


async def batch_safe_get_region(slide,
                                slide_info,
                                level,
                                start_x,
                                start_y,
                                size_x,
                                size_y,
                                image_channels,
                                vp_color,
                                z,
                                icc_intent):
    try:
        validate_image_level(slide_info, level)
        validate_image_z(slide_info, z)
        validate_image_channels(slide_info, image_channels)
        # TODO: We don't extend tiles! No need, less data transfer, faster render
        # if check_complete_region_overlap(slide_info, level, start_x, start_y, size_x, size_y):
        #     image_region = await slide.get_region(level, start_x, start_y, size_x, size_y, padding_color=vp_color, z=z)
        # else:
        #     image_region = await get_extended_region(
        #         slide.get_region, slide_info, level, start_x, start_y, size_x, size_y, padding_color=vp_color, z=z)
        return await slide.get_region(level, start_x, start_y, size_x, size_y,
                                      padding_color=vp_color, z=z, icc_intent=icc_intent)
    except Exception as e:
        logger.error(e)
        return None


async def batch_safe_get_tile(slide,
                              slide_info,
                              level,
                              tile_x,
                              tile_y,
                              image_channels,
                              vp_color,
                              z,
                              icc_intent):
    try:
        validate_image_level(slide_info, level)
        validate_image_z(slide_info, z)
        validate_image_channels(slide_info, image_channels)
        # TODO: We don't extend tiles! No need, less data transfer, faster render
        # if check_complete_tile_overlap(slide_info, level, tile_x, tile_y):
        #     image_tile = await slide.get_tile(level, tile_x, tile_y, padding_color=vp_color, z=z)
        # else:
        #     image_tile = await get_extended_tile(
        #         slide.get_tile, slide_info, level, tile_x, tile_y, padding_color=vp_color, z=z)
        tile = await slide.get_tile(level, tile_x, tile_y, padding_color=vp_color, z=z, icc_intent=icc_intent)
        return tile
    except Exception as e:
        logger.error(e)
        return None
