from typing import List
import asyncio

from PIL import Image

from wsi_service.models.v3.slide import SlideInfo
from wsi_service.utils.app_utils import (
    validate_hex_color_string,
    validate_image_request,
)
from wsi_service.utils.app_batch_utils import (
    batch_safe_make_response,
    batch_safe_get_tile,
    safe_get_slide,
    safe_get_slide_info,
    safe_get_slide_icc_profile
)
from .singletons import api_integration


async def info(paths: str, plugin: str, payload, slide_manager):
    """
    Get metadata information for a slide set (see description above sister function)
    """
    slide_ids = paths.split(",")
    requests = map(lambda sid: slide_manager.get_slide_info(sid, slide_info_model=SlideInfo, plugin=plugin),
                   slide_ids)
    slide_list = await asyncio.gather(*requests)
    requests = [api_integration.allow_access_slide(auth_payload=payload, slide_id=slide.id, manager=slide_manager,
                                                   plugin=plugin, slide=slide) for slide in slide_list]
    await asyncio.gather(*requests)
    return slide_list


async def thumbnail(
        paths: str, max_x: int, max_y: int, image_format: str, image_quality: int,
        plugin: str, icc_intent: str,
        payload, slide_manager):
    """
    Get slide SET thumbnails image  given its ID. (see description above sister function)
    """
    slide_ids = paths.split(",")
    requests = [
        api_integration.allow_access_slide(auth_payload=payload, slide_id=sid, manager=slide_manager, plugin=plugin)
        for sid in slide_ids
    ]
    await asyncio.gather(*requests)

    validate_image_request(image_format, image_quality)
    requests = map(lambda sid: safe_get_slide(slide_manager, sid, plugin=plugin), slide_ids)
    slides = await asyncio.gather(*requests)

    requests = map(lambda slide: slide.get_thumbnail(max_x, max_y, icc_intent), slides)
    thumbnails = await asyncio.gather(*requests)
    return batch_safe_make_response(slides, thumbnails, image_format, image_quality)


async def label(
            paths: str,
            max_x: int,
            max_y: int,
            image_format: str,
            image_quality: int,
            plugin: str,
            payload,
            slide_manager
    ):
        """
        Get the label image of a slide set given path(s). (see description above sister function)
        """
        slide_ids = paths.split(",")
        requests = [
            api_integration.allow_access_slide(auth_payload=payload, slide_id=sid, manager=slide_manager, plugin=plugin)
            for sid in slide_ids
        ]
        await asyncio.gather(*requests)

        validate_image_request(image_format, image_quality)
        requests = map(lambda sid: safe_get_slide(slide_manager, sid, plugin=plugin), slide_ids)
        slides = await asyncio.gather(*requests)

        requests = map(lambda slide: slide.get_label(), slides)
        labels = await asyncio.gather(*requests)
        map(lambda l: l.thumbnail((max_x, max_y), Image.ANTIALIAS), labels)
        return batch_safe_make_response(
            slides,
            labels,
            image_format,
            image_quality
        )


async def macro(
        paths: str,
        max_x: int,
        max_y: int,
        image_format: str,
        image_quality: int,
        plugin: str,
        icc_intent: str,
        payload,
        slide_manager
):
    """
    Get the macro image of a slide set given path(s). (see description above sister function)
    """
    slide_ids = paths.split(",")
    requests = [
        api_integration.allow_access_slide(auth_payload=payload, slide_id=sid, manager=slide_manager, plugin=plugin)
        for sid in slide_ids]
    await asyncio.gather(*requests)

    validate_image_request(image_format, image_quality)
    requests = map(lambda sid: safe_get_slide(slide_manager, sid, plugin=plugin), slide_ids)
    slides = await asyncio.gather(*requests)

    requests = map(lambda slide: slide.get_macro(), slides)
    macros = await asyncio.gather(*requests)
    map(lambda m: m.thumbnail((max_x, max_y), Image.ANTIALIAS), macros)
    return batch_safe_make_response(
        slides,
        macros,
        image_format,
        image_quality
    )


async def tile(
        paths: str,
        level: int,
        tile_x: int,
        tile_y: int,
        image_channels: List[int],
        z: int,
        padding_color: str,
        image_format: str,
        image_quality: int,
        icc_intent: str,
        plugin: str,
        payload,
        slide_manager
):
    """
    Get a tile of a slide given its path (see description above sister function)
    """
    slide_ids = paths.split(",")
    requests = [
        api_integration.allow_access_slide(auth_payload=payload, slide_id=sid, manager=slide_manager, plugin=plugin)
        for sid in slide_ids]
    await asyncio.gather(*requests)

    vp_color = validate_hex_color_string(padding_color)
    validate_image_request(image_format, image_quality)

    requests = map(lambda sid: safe_get_slide(slide_manager, sid, plugin=plugin), slide_ids)
    slides = await asyncio.gather(*requests)

    requests = map(safe_get_slide_info, slides)
    slide_infos = await asyncio.gather(*requests)
    requests = map(lambda i: batch_safe_get_tile(slides[i], slide_infos[i],
                                                 level, tile_x, tile_y,
                                                 image_channels, vp_color, z),
                   range(slides.__len__()))
    regions = await asyncio.gather(*requests)
    return batch_safe_make_response(slides, regions, image_format, image_quality, image_channels)


async def batch(
        paths: str,
        levels: str,
        xs: str,
        ys: str,
        image_channels: List[int],
        z: int, # todo, also?
        padding_color: str,
        image_format: str,
        image_quality: int,
        icc_intent: str,
        plugin: str,
        payload,
        slide_manager
):
    """
    Get a tile of a slide given its path (see description above sister function)
    """
    slide_ids = paths.split(",")
    requests = [
        api_integration.allow_access_slide(auth_payload=payload, slide_id=sid, manager=slide_manager, plugin=plugin)
        for sid in slide_ids]
    await asyncio.gather(*requests)

    vp_color = validate_hex_color_string(padding_color)
    validate_image_request(image_format, image_quality)
    requests = map(lambda sid: safe_get_slide(slide_manager, sid, plugin=plugin), slide_ids)
    slides = await asyncio.gather(*requests)

    requests = map(safe_get_slide_info, slides)
    slide_infos = await asyncio.gather(*requests)

    xs = [int(x) for x in xs.split(',')]
    ys = [int(x) for x in ys.split(',')]
    levels = [int(x) for x in levels.split(',')]
    requests = map(lambda i: batch_safe_get_tile(slides[i], slide_infos[i],
                                                 levels[i], xs[i], ys[i],
                                                 image_channels, vp_color, z, icc_intent),
                   range(slides.__len__()))

    regions = await asyncio.gather(*requests)
    return batch_safe_make_response(slides, regions, image_format, image_quality, image_channels)


async def icc_profile(
        paths: str,
        plugin: str,
        payload,
        slide_manager
):
    slide_ids = paths.split(",")
    requests = [
        api_integration.allow_access_slide(auth_payload=payload, slide_id=sid, manager=slide_manager, plugin=plugin)
        for sid in slide_ids]
    await asyncio.gather(*requests)

    requests = map(lambda sid: safe_get_slide(slide_manager, sid, plugin=plugin), slide_ids)
    slides = await asyncio.gather(*requests)

    requests = map(safe_get_slide_icc_profile, slides)
    profiles = await asyncio.gather(*requests)
    return batch_safe_make_response(slides, profiles, "raw", None, None)