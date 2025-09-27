from io import BytesIO
from typing import Optional, Tuple

import numpy as np
from fastapi import HTTPException
from PIL import Image

from wsi_service.custom_models.queries import ICCProfileIntent


def rgba_to_rgb_with_background_color(image_rgba, padding_color):
    if image_rgba.info.get("transparency", None) is not None or image_rgba.mode == "RGBA":
        image_rgb = Image.new("RGB", image_rgba.size, padding_color)
        image_rgb.paste(image_rgba, mask=image_rgba.split()[3])
    else:
        image_rgb = image_rgba.convert("RGB")
    return image_rgb


def convert_narray_uintX_to_uint8(array, exp=16, lower=None, upper=None):
    if exp not in [8, 16, 32, 64]:
        raise ValueError("Only exponent in range [8, 16, 32, 64] supported")
    if lower is not None and not (0 <= lower < 2**exp):
        raise ValueError(f"lower bound must be between 0 and 2**{exp}")
    if upper is not None and not (0 <= upper < 2**exp):
        raise ValueError(f"upper bound must be between 0 and 2**{exp}")
    if not lower and not upper and exp == 8:
        return array
    if lower is None:
        lower = 0
    if upper is None:
        upper = (2**exp) - 1
        # default upper bound for bitness > 8 to enhance contrast/brightness
        if exp > 8:
            upper = (2**exp) / (exp / 4)

    temp_array = np.divide((array - lower), (upper - lower))
    temp_array = np.clip(temp_array * 255, 0, 255)
    return temp_array.astype(np.uint8)


def convert_int_to_rgba_array(i):
    return [(i >> 24) & 0xFF, (i >> 16) & 0xFF, (i >> 8) & 0xFF, i & 0xFF]


def convert_rgba_array_to_int(rgba):
    return int.from_bytes(rgba, byteorder="big", signed=True)


def convert_rgb_image_for_channels(image_tile, image_channel):
    r = 1 if 0 in image_channel else 0
    g = 1 if 1 in image_channel else 0
    b = 1 if 2 in image_channel else 0
    conv_matrix = (r, 0, 0, 0, 0, g, 0, 0, 0, 0, b, 0)
    converted_image = image_tile.convert("RGB", conv_matrix)
    return converted_image


def convert_rgb_image_by_color(image_tile, rgba):
    conv_matrix = (rgba[0] / 255, 0, 0, 0, 0, rgba[1] / 255, 0, 0, 0, 0, rgba[2] / 255, 0)
    converted_image = image_tile.convert("RGB", conv_matrix)
    return converted_image


def convert_narray_to_pil_image(narray, lower=None, upper=None, mode="RGB"):
    if narray.dtype == np.uint8:
        narray_uint8 = narray
    elif narray.dtype == np.uint16:
        narray_uint8 = convert_narray_uintX_to_uint8(narray, 16, lower, upper)
    elif narray.dtype in [np.uint32, np.float32]:
        narray_uint8 = convert_narray_uintX_to_uint8(narray, 32, lower, upper)
    elif narray.dtype in [np.uint64, np.float64]:
        narray_uint8 = convert_narray_uintX_to_uint8(narray, 64, lower, upper)
    else:
        raise HTTPException(status_code=400, detail="Array conversion not supported")

    try:
        if mode == "L" or narray_uint8.shape[0] == 1:
            # convert to grayscale for single channel
            new_array = narray_uint8[0, :, :]
            pil_image = Image.fromarray(new_array, mode="L")
        else:
            # we need to transpose the array here to make it readable for pillow (width, height, channel)
            narray_uint8 = np.ascontiguousarray(narray_uint8.transpose(1, 2, 0))
            pil_image = Image.fromarray(narray_uint8, mode="RGB")
        return pil_image
    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"Image conversion to Pillow failed: {err}")


def save_rgb_image(pil_image, image_format, image_quality):
    mem = BytesIO()
    pil_image.save(mem, format=image_format, quality=image_quality)
    mem.seek(0)
    return mem


def get_requested_channels_as_rgb_array(narray, image_channels, slide):
    separate_channels = np.vsplit(narray, narray.shape[0])

    temp_array = []
    if image_channels is not None and len(image_channels) == 1:
        # edge case 1: single channel will be converted to a grayscale image
        return separate_channels[image_channels[0]]
    elif image_channels is not None and len(image_channels) == 2:
        # edge case 2: we cast two dedicated image to an rgb image if requested
        temp_array.append(separate_channels[image_channels[0]])
        temp_array.append(separate_channels[image_channels[1]])
        temp_array.append(np.zeros(separate_channels[image_channels[0]].shape))
    else:
        # three or more channels given
        # in this case we simply return the first 3 channels for now
        temp_array = get_multi_channel_as_rgb(separate_channels)

    result = np.concatenate(temp_array, axis=0)
    return result


def get_multi_channel_as_rgb(separate_channels):
    # right now only three channels are considered
    temp_array = []
    for channel in separate_channels:
        if len(temp_array) == 3:
            break
        temp_array.append(channel)
    return temp_array


def get_single_channel(separate_channels, channel, color):
    temp_array = []
    for i in range(3):
        c = color.r if i == 0 else (color.g if i == 1 else color.b)
        temp_channel = separate_channels[channel] * (c / 255)
        temp_array.append(temp_channel)
    return temp_array


def get_requested_channels_as_array(narray, image_channels):
    if narray.shape[0] == len(image_channels):
        return narray

    separate_channels = np.vsplit(narray, narray.shape[0])
    temp_array = []
    for i in image_channels:
        temp_array.append(separate_channels[i])
    result = np.concatenate(temp_array, axis=0)
    return result


def check_complete_region_overlap(slide_info, level, start_x, start_y, size_x, size_y):
    return (
        start_x >= 0
        and start_y >= 0
        and start_x + size_x < slide_info.levels[level].extent.x
        and start_y + size_y < slide_info.levels[level].extent.y
    )


_REGION_PROTO_CACHE = {}

def _region_intersection(slide_info, level: int, start_x: int, start_y: int, size_x: int, size_y: int):
    """Compute intersection of requested region with the level extent.
    Returns: (ov_w, ov_h, src_x, src_y, dst_x, dst_y)
      - src_* are the clamped coords to request from the slide
      - dst_* are the paste offsets in the output canvas when extending
    """
    lvl_w = slide_info.levels[level].extent.x
    lvl_h = slide_info.levels[level].extent.y

    # where we can actually read from
    src_x = max(0, start_x)
    src_y = max(0, start_y)
    src_x2 = min(lvl_w, start_x + size_x)
    src_y2 = min(lvl_h, start_y + size_y)

    ov_w = max(0, src_x2 - src_x)
    ov_h = max(0, src_y2 - src_y)

    # where to paste the overlap into the requested canvas
    dst_x = max(0, -start_x)
    dst_y = max(0, -start_y)
    return ov_w, ov_h, src_x, src_y, dst_x, dst_y


async def _region_prototype(get_region, slide_info, level, padding_color, z, icc_profile_intent, icc_profile_strict):
    """Fetch a 1×1 sample (once) to preserve type/mode/dtype for empty canvases."""
    key = (id(slide_info), level)
    if key in _REGION_PROTO_CACHE:
        return _REGION_PROTO_CACHE[key]
    # request something guaranteed in-bounds
    proto = await get_region(level, 0, 0, 1, 1,
                             padding_color=padding_color, z=z,
                             icc_profile_intent=icc_profile_intent,
                             icc_profile_strict=icc_profile_strict)
    if isinstance(proto, bytes):
        proto = Image.open(BytesIO(proto))
    _REGION_PROTO_CACHE[key] = proto
    return proto


async def get_extended_region(
    get_region,
    slide_info,
    level: int,
    start_x: int,
    start_y: int,
    size_x: int,
    size_y: int,
    *,
    padding_color=None,
    z: int = 0,
    icc_profile_intent: ICCProfileIntent = None,
    icc_profile_strict: bool = False,
    extend: bool = True,
):
    """
    Normalize edge/out-of-bounds regions.

      - extend=True  -> return a full requested (size_x × size_y) canvas, padding uncovered area.
      - extend=False -> return only the *real* overlap (shrunk region), possibly smaller than requested.

    Guarantees a single read for partial overlaps. For fully OOB:
      - extend=True returns a padded canvas
      - extend=False raises 416
    """
    ov_w, ov_h, src_x, src_y, dst_x, dst_y = _region_intersection(
        slide_info, level, start_x, start_y, size_x, size_y
    )

    # No overlap at all
    if ov_w == 0 or ov_h == 0:
        if not extend:
            raise HTTPException(status_code=416, detail="Requested region is outside the image extent")
        proto = await _region_prototype(get_region, slide_info, level, padding_color, z,
                                        icc_profile_intent, icc_profile_strict)
        if isinstance(proto, Image.Image):
            mode = proto.mode or "RGB"
            return Image.new(mode, (size_x, size_y), padding_color)
        else:
            C = proto.shape[0]
            out = np.empty((C, size_y, size_x), dtype=proto.dtype)
            if padding_color is None:
                out.fill(0)
            else:
                if np.isscalar(padding_color):
                    out[...] = padding_color
                else:
                    col = np.asarray(padding_color, dtype=proto.dtype).reshape(-1, 1, 1)
                    if col.shape[0] != C:
                        raise ValueError(f"padding_color channels ({col.shape[0]}) != region channels ({C})")
                    out[...] = col
            return out

    # Partial or full overlap -> one read
    src = await get_region(
        level, src_x, src_y, ov_w, ov_h,
        padding_color=padding_color, z=z,
        icc_profile_intent=icc_profile_intent, icc_profile_strict=icc_profile_strict,
    )
    if isinstance(src, bytes):
        src = Image.open(BytesIO(src))

    # Full overlap that exactly matches requested size? (This path is rarely reached because the endpoint
    # already guards it, but it's safe and avoids extra copies.)
    if ov_w == size_x and ov_h == size_y and start_x >= 0 and start_y >= 0:
        return src

    if not extend:
        # SHRINK: return just the real content
        return src

    # EXTEND: compose a full requested canvas and paste the overlap at the right offset
    if isinstance(src, Image.Image):
        mode = src.mode or "RGB"
        out = Image.new(mode, (size_x, size_y), padding_color)
        out.paste(src, (dst_x, dst_y))
        return out
    else:
        C = src.shape[0]
        out = np.empty((C, size_y, size_x), dtype=src.dtype)
        if padding_color is None:
            out.fill(0)
        else:
            if np.isscalar(padding_color):
                out[...] = padding_color
            else:
                col = np.asarray(padding_color, dtype=src.dtype).reshape(-1, 1, 1)
                if col.shape[0] != C:
                    raise ValueError(f"padding_color channels ({col.shape[0]}) != region channels ({C})")
                out[...] = col
        out[:, dst_y:dst_y + ov_h, dst_x:dst_x + ov_w] = src
        return out


def check_complete_tile_overlap(slide_info, level, tile_x, tile_y):
    tile_count_x = int(slide_info.levels[level].extent.x / slide_info.tile_extent.x)
    tile_count_y = int(slide_info.levels[level].extent.y / slide_info.tile_extent.y)
    return tile_x >= 0 and tile_y >= 0 and tile_x < tile_count_x and tile_y < tile_count_y


def check_complete_tile_overlap(slide_info, level: int, tile_x: int, tile_y: int) -> bool:
    """
    Returns True if the (tile_x, tile_y) tile at 'level' is fully contained within the level extent.
    """
    tile_w, tile_h = slide_info.tile_extent.x, slide_info.tile_extent.y
    lvl_w, lvl_h   = slide_info.levels[level].extent.x, slide_info.levels[level].extent.y

    x0 = tile_x * tile_w
    y0 = tile_y * tile_h
    return (x0 >= 0) and (y0 >= 0) and (x0 + tile_w) <= lvl_w and (y0 + tile_h) <= lvl_h


def _overlap_wh(slide_info, level: int, tile_x: int, tile_y: int) -> Tuple[int, int]:
    """Clamped overlap size (width,height) of the tile with the level image."""
    tile_w, tile_h = slide_info.tile_extent.x, slide_info.tile_extent.y
    lvl_w,  lvl_h  = slide_info.levels[level].extent.x, slide_info.levels[level].extent.y
    x0 = tile_x * tile_w
    y0 = tile_y * tile_h
    ov_w = max(0, min(tile_w, lvl_w - x0))
    ov_h = max(0, min(tile_h, lvl_h - y0))
    return ov_w, ov_h


async def get_extended_tile(
    get_tile,
    slide_info,
    level: int,
    tile_x: int,
    tile_y: int,
    *,
    padding_color=None,
    z: int = 0,
    icc_profile_intent=None,
    icc_profile_strict: bool = False,
    extend: bool = True,
):
    """
    Wraps `get_tile` and normalizes edge tiles:

      - extend=True  -> return a full-size (tile_w x tile_h) tile, padding the uncovered area.
      - extend=False -> return a cropped tile containing ONLY real pixels (shrunk edge).

    Guarantees:
      - Only one call to `get_tile(...)`.
      - Returns the same type as `get_tile`: PIL.Image.Image or numpy array shaped (C, H, W).
      - No extra reads to 'sample' type.
    """
    tile = await get_tile(
        level, tile_x, tile_y,
        padding_color=padding_color,
        z=z,
        icc_profile_intent=icc_profile_intent,
        icc_profile_strict=icc_profile_strict,
    )
    if isinstance(tile, bytes):
        tile = Image.open(BytesIO(tile))

    tile_w, tile_h = slide_info.tile_extent.x, slide_info.tile_extent.y
    ov_w, ov_h = _overlap_wh(slide_info, level, tile_x, tile_y)

    # Fast path: interior tile (already exact full tile)
    if ov_w == tile_w and ov_h == tile_h:
        return tile

    # Edge path
    if not extend:
        # --- SHRINK: crop away any padded area / outside-of-level region
        if isinstance(tile, Image.Image):
            return tile.crop((0, 0, ov_w, ov_h))
        else:
            # numpy: assume C x H x W
            return tile[:, :ov_h, :ov_w]

    # --- EXTEND: paste/copy the valid region into a full-size buffer
    if isinstance(tile, Image.Image):
        mode = tile.mode or "RGB"
        bg   = padding_color if padding_color is not None else 0  # 0 works for L/RGB/RGBA (transparent black in RGBA)
        out = Image.new(mode, (tile_w, tile_h), bg)
        # only copy real content; avoid re-padding the padded part
        out.paste(tile.crop((0, 0, ov_w, ov_h)), (0, 0))
        return out
    else:
        # numpy: C x H x W
        C = tile.shape[0]
        out = np.empty((C, tile_h, tile_w), dtype=tile.dtype)
        if padding_color is None:
            out.fill(0)
        else:
            if np.isscalar(padding_color):
                out[...] = padding_color
            else:
                col = np.asarray(padding_color, dtype=tile.dtype).reshape(-1, 1, 1)
                if col.shape[0] != C:
                    raise ValueError(f"padding_color channels ({col.shape[0]}) != tile channels ({C})")
                out[...] = col
        out[:, :ov_h, :ov_w] = tile[:, :ov_h, :ov_w]
        return out