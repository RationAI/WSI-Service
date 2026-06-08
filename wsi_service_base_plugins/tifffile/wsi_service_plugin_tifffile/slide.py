import re
from threading import Lock
from PIL import Image

import numpy as np
import tifffile
from defusedxml import ElementTree as xml
from fastapi import HTTPException
from skimage import transform, util

from wsi_service.models.v3.slide import SlideChannel, SlideColor, SlideExtent, SlideInfo, SlidePixelSizeNm
from wsi_service.singletons import logger, settings
from wsi_service.slide import Slide as BaseSlide
from wsi_service.utils.icc_profile import ICCProfile, ICCProfileError
from wsi_service.utils.image_utils import convert_int_to_rgba_array, convert_narray_to_pil_image
from wsi_service.utils.slide_utils import get_original_levels

_LAYOUT_PAGE_PER_CHANNEL = "page-per-channel"
_LAYOUT_CHUNKY_SAMPLES = "chunky-samples"
_LAYOUT_SINGLE_CHANNEL = "single-channel"

# Fallback palette cycled through for synthesized channels with no metadata hint.
_DEFAULT_PALETTE = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 0),
    (255, 255, 255),
]


class Slide(BaseSlide):
    async def open(self, filepath):
        self.locker = Lock()
        try:
            self.tif_slide = tifffile.TiffFile(filepath)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Failed to load tiff file. [{e}]")

        if self.tif_slide.is_ome:
            try:
                self.ome_metadata = self.tif_slide.ome_metadata
                self.parsed_metadata = xml.fromstring(self.ome_metadata)
            except Exception as ex:
                raise HTTPException(status_code=400, detail=f"Could not obtain ome metadata ({ex})")
            self.slide_info = self.__get_slide_info_ome_tif()
            self.layout = _LAYOUT_PAGE_PER_CHANNEL
        else:
            self.slide_info, self.layout = self.__get_slide_info_generic_tif()

        self._icc = ICCProfile()

    async def close(self):
        self.tif_slide.close()
        self._icc.free_cache()

    async def get_info(self):
        return self.slide_info

    async def get_region(self, level, start_x, start_y, size_x, size_y, padding_color=None, z=0,
                         icc_profile_intent: str = None, icc_profile_strict: bool = False):
        if padding_color is None:
            padding_color = settings.padding_color
        level_slide = self.slide_info.levels[level]
        tif_level = self.__get_tif_level_for_slide_level(level_slide)

        result = self.__assemble_region(tif_level, start_x, start_y, size_x, size_y, padding_color)

        if icc_profile_intent is not None:
            try:
                profile = tif_level.pages[0].tags.get("ICCProfile")
                result_data = convert_narray_to_pil_image(narray=result)
                result = self._icc.process_pil_image(
                    result_data, profile, icc_profile_strict, icc_profile_intent, True
                )
            except ICCProfileError as e:
                raise HTTPException(status_code=e.payload["status_code"], detail=e.payload["detail"]) from e

        return result

    async def get_thumbnail(self, max_x, max_y, icc_profile_intent: str = None, icc_profile_strict: bool = False):
        thumb_level = len(self.slide_info.levels) - 1
        for i, level in enumerate(self.slide_info.levels):
            if level.extent.x < max_x or level.extent.y < max_y:
                thumb_level = i
                break
        level_extent_x = self.slide_info.levels[thumb_level].extent.x
        level_extent_y = self.slide_info.levels[thumb_level].extent.y

        if max_x > max_y:
            max_y = max_y * (level_extent_y / level_extent_x)
        else:
            max_x = max_x * (level_extent_x / level_extent_y)
        thumbnail_org = await self.get_region(thumb_level, 0, 0, level_extent_x, level_extent_y,
                                              settings.padding_color, 0, icc_profile_intent, icc_profile_strict)
        if type(thumbnail_org) is np.ndarray:
            thumbnail_resized = util.img_as_uint(transform.resize(thumbnail_org, (thumbnail_org.shape[0], max_y, max_x)))
        else:
            thumbnail_resized = thumbnail_org.resize((max_x, max_y), Image.LANCZOS)
        return thumbnail_resized

    async def get_label(self):
        self.__get_associated_image("label")

    async def get_macro(self, icc_profile_intent: str = None, icc_profile_strict: bool = False):
        self.__get_associated_image("macro")

    async def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0,
                       icc_profile_intent: str = None, icc_profile_strict: bool = False):
        return await self.get_region(
            level,
            tile_x * self.slide_info.tile_extent.x,
            tile_y * self.slide_info.tile_extent.y,
            self.slide_info.tile_extent.x,
            self.slide_info.tile_extent.y,
            padding_color,
            0,
            icc_profile_intent,
            icc_profile_strict,
        )

    async def get_icc_profile(self):
        return self._icc.get_for_payload(self.tif_slide.series[0].levels[0].pages[0].tags.get("ICCProfile", None))

    # private

    def __get_associated_image(self, associated_image_name):
        raise HTTPException(
            status_code=404,
            detail=f"Associated image {associated_image_name} does not exist.",
        )

    def __get_color_for_channel(self, channel_index, channel_depth, padding_color):
        if channel_depth == 8:
            if padding_color is None:
                padding_color = settings.padding_color
            rgb_color = padding_color[channel_index if channel_index < 2 else 2]
        else:
            # when image depth is higher than 8bit we set default value to zero to make background black:
            # currently channels with more than 8bits bitness are mapped to rgb by distributing color values
            # depending on lowest and highest intensity. therefore mapping colors back and forth will
            # result in undefined behaviour of the padding color
            rgb_color = 0
        return rgb_color

    def __get_tif_level_for_slide_level(self, slide_level):
        for level in self.tif_slide.series[0].levels:
            keyframe = level.keyframe
            if keyframe.imagelength == slide_level.extent.y and keyframe.imagewidth == slide_level.extent.x:
                return level
        return None

    def __assemble_region(self, tif_level, start_x, start_y, size_x, size_y, padding_color):
        if self.layout == _LAYOUT_CHUNKY_SAMPLES:
            # Single page holds all channels in the last axis (samplesperpixel).
            page = tif_level.pages[0]
            if not page.keyframe.is_tiled:
                # __read_region_of_page_untiled allocates a 2-D (H, W) output and would crash
                # when assigning the (H, W, S) slice from page.asarray(). Read directly here.
                page_frame = page.keyframe
                page_width, page_height = page_frame.imagewidth, page_frame.imagelength
                page_array = page.asarray()
                if page_array.ndim == 2:
                    page_array = np.expand_dims(page_array, axis=-1)
                new_height = page_height - start_y if (start_y + size_y > page_height) else size_y
                new_width = page_width - start_x if (start_x + size_x > page_width) else size_x
                S = page_frame.samplesperpixel
                out = np.empty((S, size_y, size_x), dtype=page_frame.dtype)
                for s in range(S):
                    fill_val = self.__get_color_for_channel(s, self.slide_info.channel_depth, padding_color)
                    out[s].fill(fill_val)
                if new_height > 0 and new_width > 0:
                    crop = page_array[start_y : start_y + new_height, start_x : start_x + new_width]
                    out[:, 0:new_height, 0:new_width] = np.moveaxis(crop, -1, 0)
                return out

            channel_data = self.__read_region_of_page(page, 0, start_y, start_x, size_y, size_x, padding_color)
            # channel_data shape from tiled path: (Z, H, W, S); from untiled path: (1, H, W, 1).
            arr = np.asarray(channel_data)
            if arr.ndim == 4:
                # (Z, H, W, S) -> (S, H, W) by squeezing Z=1 and moving S to front.
                arr = arr[0]                       # (H, W, S)
                arr = np.moveaxis(arr, -1, 0)      # (S, H, W)
            elif arr.ndim == 3:
                # (Z, H, W) for an untiled single-sample read — shouldn't happen for chunky, but guard.
                arr = arr[0:1]
            return arr

        if self.layout == _LAYOUT_SINGLE_CHANNEL:
            page = tif_level.pages[0]
            channel_data = self.__read_region_of_page(page, 0, start_y, start_x, size_y, size_x, padding_color)
            arr = np.asarray(channel_data)
            # Drop trailing sample axis if present (== 1), keep leading Z axis as the single channel.
            if arr.ndim == 4:
                arr = arr[:, :, :, 0]
            return arr

        # _LAYOUT_PAGE_PER_CHANNEL — original behavior, one page per channel.
        result_array = []
        for i, page in enumerate(tif_level.pages):
            temp_channel = self.__read_region_of_page(page, i, start_y, start_x, size_y, size_x, padding_color)
            result_array.append(temp_channel)
        return np.concatenate(result_array, axis=0)[:, :, :, 0]

    def __read_region_of_page(self, page, channel_index, start_x, start_y, size_x, size_y, padding_color):
        page_frame = page.keyframe

        if not page_frame.is_tiled:
            result = self.__read_region_of_page_untiled(
                page, channel_index, start_x, start_y, size_x, size_y, padding_color
            )
            if result.size == 0:
                result = np.full(
                    (size_x, size_y),
                    self.__get_color_for_channel(channel_index, self.slide_info.channel_depth, padding_color),
                    dtype=page_frame.dtype,
                )
        else:
            result = self.__read_region_of_page_tiled(
                page, channel_index, start_x, start_y, size_x, size_y, padding_color
            )
            if result.size == 0:
                result = np.full(
                    (page_frame.imagedepth, size_x, size_y, page_frame.samplesperpixel),
                    self.__get_color_for_channel(channel_index, self.slide_info.channel_depth, padding_color),
                    dtype=page_frame.dtype,
                )

        return result

    def __read_region_of_page_untiled(self, page, channel_index, start_x, start_y, size_x, size_y, padding_color):
        page_frame = page.keyframe
        page_width, page_height = page_frame.imagewidth, page_frame.imagelength
        page_array = page.asarray()

        new_height = page_height - start_x if (start_x + size_x > page_height) else size_x
        new_width = page_width - start_y if (start_y + size_y > page_width) else size_y

        out = np.full(
            (size_x, size_y),
            self.__get_color_for_channel(channel_index, self.slide_info.channel_depth, padding_color),
            dtype=page_frame.dtype,
        )

        out[0:new_height, 0:new_width] = page_array[start_x : start_x + new_height, start_y : start_y + new_width]
        return np.expand_dims(np.expand_dims(out, axis=0), axis=3)

    def __read_region_of_page_tiled(self, page, channel_index, start_x, start_y, size_x, size_y, padding_color):
        page_frame = page.keyframe
        image_width, image_height = page_frame.imagewidth, page_frame.imagelength

        # Region entirely outside the image — let the caller produce a padding-only tile via the
        # `result.size == 0` branch instead of letting np.full crash on a negative dimension.
        if start_x >= image_height or start_y >= image_width or start_x + size_x <= 0 or start_y + size_y <= 0:
            return np.empty(
                (page_frame.imagedepth, 0, 0, page_frame.samplesperpixel),
                dtype=page_frame.dtype,
            )

        tile_width, tile_height = page_frame.tilewidth, page_frame.tilelength
        end_x = (start_x + size_x) if (start_x + size_x) < image_height else image_height
        end_y = (start_y + size_y) if (start_y + size_y) < image_width else image_width

        start_tile_x0, start_tile_y0 = start_x // tile_height, start_y // tile_width
        end_tile_xn, end_tile_yn = np.ceil([end_x / tile_height, end_y / tile_width]).astype(int)

        tile_per_line = int(np.ceil(image_width / tile_width))

        # initialize array with size of all relevant tiles
        out = np.full(
            (
                page_frame.imagedepth,
                (end_tile_xn - start_tile_x0) * tile_height,
                (end_tile_yn - start_tile_y0) * tile_width,
                page_frame.samplesperpixel,
            ),
            self.__get_color_for_channel(channel_index, self.slide_info.channel_depth, padding_color),
            dtype=page_frame.dtype,
        )
        fh = page.parent.filehandle

        if fh is None:
            raise HTTPException(
                status_code=422,
                detail="Could not read from tiff file. File handle is null",
            )

        jpegtables = page.jpegtables
        if jpegtables is not None:
            jpegtables = jpegtables.value

        used_offsets = []
        # iterate through tiles starting at the top left to the bottom right
        for i in range(start_tile_x0, end_tile_xn):
            for j in range(start_tile_y0, end_tile_yn):
                with self.locker:
                    index = int(i * tile_per_line + j)

                    if len(page.dataoffsets) <= index:
                        continue

                    offset = page.dataoffsets[index]
                    bytecount = page.databytecounts[index]

                    if offset in used_offsets:
                        continue

                    used_offsets.append(offset)

                    # search to tile offset and read image tile
                    fh.seek(offset)
                    if fh.tell() != offset:
                        raise HTTPException(status_code=500, detail="Failed reading to tile offset")
                    data = fh.read(bytecount)
                    tile, _, _ = page.decode(data, index, jpegtables=jpegtables)

                    # insert tile in temporary output array
                    tile_position_i = (i - start_tile_x0) * tile_height
                    tile_position_j = (j - start_tile_y0) * tile_width

                    out[
                        :,
                        tile_position_i : tile_position_i + tile_height,
                        tile_position_j : tile_position_j + tile_width :,
                    ] = tile

        # determine the new start positions of our region
        new_start_x = start_x - start_tile_x0 * tile_height
        new_start_y = start_y - start_tile_y0 * tile_width

        # restrict the output array to the requested region
        result = out[:, new_start_x : new_start_x + size_x, new_start_y : new_start_y + size_y :]
        return result

    def __get_levels_from_series(self, tif_slide):
        levels = tif_slide.series[0].levels
        level_count = len(levels)
        level_dimensions = []
        level_downsamples = []

        for i, item in enumerate(levels):
            level_dimensions.append([item.keyframe.imagewidth, item.keyframe.imagelength])
            if i > 0:
                level_downsamples.append(level_dimensions[0][0] / item.keyframe.imagewidth)
            else:
                level_downsamples.append(1)

        return get_original_levels(level_count, level_dimensions, level_downsamples)

    def __get_xml_namespace(self):
        m = re.match(r"\{.*\}", self.parsed_metadata.tag)
        return m.group(0) if m else ""

    def __get_channels_ome_tif(self):
        namespace = self.__get_xml_namespace()
        xml_channels = (
            self.parsed_metadata.find(f"{ namespace }Image")
            .find(f"{ namespace }Pixels")
            .findall(f"{ namespace }Channel")
        )
        channels = []
        for i, xmlc in enumerate(xml_channels):
            color_int = convert_int_to_rgba_array(int(xmlc.get("Color")))
            temp_channel = SlideChannel(
                id=i,
                name=xmlc.get("Name"),
                color=SlideColor(r=color_int[0], g=color_int[1], b=color_int[2], a=color_int[3]),
            )
            channels.append(temp_channel)
        return channels

    def __get_pixel_size_ome_tif(self):
        namespace = self.__get_xml_namespace()
        pixel_unit_x = (
            self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").get("PhysicalSizeXUnit")
        )
        pixel_unit_y = (
            self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").get("PhysicalSizeYUnit")
        )
        if pixel_unit_x != pixel_unit_y:
            raise HTTPException(
                status_code=500,
                detail="Different pixel size unit in x- and y-direction not supported.",
            )
        pixel_size_x = (
            self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").get("PhysicalSizeX")
        )
        pixel_size_y = (
            self.parsed_metadata.find(f"{ namespace }Image").find(f"{ namespace }Pixels").get("PhysicalSizeY")
        )
        if pixel_unit_x == "nm":
            return SlidePixelSizeNm(x=float(pixel_size_x), y=float(pixel_size_y))
        elif pixel_unit_x == "µm":
            x = float(pixel_size_x) * 1000
            y = float(pixel_size_y) * 1000
            return SlidePixelSizeNm(x=x, y=y)
        elif pixel_unit_x == "cm":
            x = float(pixel_size_x) * 1e6
            y = float(pixel_size_y) * 1e6
            return SlidePixelSizeNm(x=x, y=y)
        else:
            raise HTTPException(status_code=500, detail=f"Invalid pixel size unit ({pixel_unit_x})")

    def __get_slide_info_ome_tif(self):
        serie = self.tif_slide.series[0]
        channels = self.__get_channels_ome_tif()
        pixel_size = self.__get_pixel_size_ome_tif()
        levels = self.__get_levels_from_series(self.tif_slide)
        try:
            slide_info = SlideInfo(
                id="",
                channels=channels,
                channel_depth=serie.keyframe.bitspersample,
                extent=SlideExtent(
                    x=serie.keyframe.imagewidth,
                    y=serie.keyframe.imagelength,
                    z=serie.keyframe.imagedepth,
                ),
                pixel_size_nm=pixel_size,
                tile_extent=SlideExtent(
                    x=serie.keyframe.tilewidth,
                    y=serie.keyframe.tilelength,
                    z=serie.keyframe.tiledepth,
                ),
                num_levels=len(levels),
                levels=levels,
                format="ome-tiff",
            )
            return slide_info
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Failed to gather slide infos. [{e}]")

    # --- Generic (non-OME) TIFF support ---

    def __get_slide_info_generic_tif(self):
        serie = self.tif_slide.series[0]
        keyframe = serie.keyframe

        layout, num_channels = self.__detect_generic_layout(serie, keyframe)
        channels = self.__get_channels_generic(num_channels, keyframe)
        pixel_size = self.__get_pixel_size_generic(keyframe)
        levels = self.__get_levels_from_series(self.tif_slide)

        if keyframe.is_tiled:
            tile_extent = SlideExtent(
                x=keyframe.tilewidth,
                y=keyframe.tilelength,
                z=keyframe.tiledepth,
            )
        else:
            tile_extent = SlideExtent(x=256, y=256, z=1)

        try:
            slide_info = SlideInfo(
                id="",
                channels=channels,
                channel_depth=keyframe.bitspersample,
                extent=SlideExtent(
                    x=keyframe.imagewidth,
                    y=keyframe.imagelength,
                    z=keyframe.imagedepth,
                ),
                pixel_size_nm=pixel_size,
                tile_extent=tile_extent,
                num_levels=len(levels),
                levels=levels,
                format="tiff-multichannel",
            )
            return slide_info, layout
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Failed to gather slide infos. [{e}]")

    def __detect_generic_layout(self, serie, keyframe):
        axes = str(getattr(serie, "axes", "") or "")
        shape = tuple(getattr(serie, "shape", ()) or ())
        samples = int(getattr(keyframe, "samplesperpixel", 1) or 1)
        page_count = len(serie.pages)

        for ch in ("C", "S"):
            if ch in axes:
                idx = axes.index(ch)
                if idx < len(shape) and shape[idx] > 1 and page_count > 1:
                    return _LAYOUT_PAGE_PER_CHANNEL, int(shape[idx])

        if page_count > 1 and samples == 1:
            return _LAYOUT_PAGE_PER_CHANNEL, page_count

        if samples > 1:
            return _LAYOUT_CHUNKY_SAMPLES, samples

        return _LAYOUT_SINGLE_CHANNEL, 1

    def __get_channels_generic(self, num_channels, keyframe):
        names = self.__extract_channel_names(num_channels, keyframe)
        colors = self.__extract_channel_colors(num_channels)

        channels = []
        for i in range(num_channels):
            name = names[i] if i < len(names) and names[i] else f"Channel {i}"
            r, g, b = colors[i]
            channels.append(
                SlideChannel(id=i, name=name, color=SlideColor(r=r, g=g, b=b, a=0))
            )
        return channels

    def __extract_channel_names(self, num_channels, keyframe):
        # 1) ImageJ metadata (tifffile parses Labels into imagej_metadata).
        try:
            ij = getattr(self.tif_slide, "imagej_metadata", None) or {}
            labels = ij.get("Labels")
            if isinstance(labels, (list, tuple)) and len(labels) > 0:
                return [str(x) for x in labels[:num_channels]]
        except Exception:
            pass

        # 2) ImageDescription scanner hints — Bio-Formats / Leica / Zeiss style.
        try:
            description = getattr(keyframe, "description", "") or ""
            if description:
                # Bio-Formats: "Channel:0:Name=DAPI"
                bf = re.findall(r"Channel:\d+:Name=([^\r\n]+)", description)
                if len(bf) > 0:
                    return [s.strip() for s in bf[:num_channels]]
                # Generic "ChannelName=Foo" or "Channel 0 Name = Foo"
                generic = re.findall(r"Channel(?:Name|\s*\d+\s*Name)\s*=\s*([^\r\n]+)", description)
                if len(generic) > 0:
                    return [s.strip() for s in generic[:num_channels]]
        except Exception:
            pass

        return []

    def __extract_channel_colors(self, num_channels):
        # 1) ImageJ LUTs (each entry is a (3, 256) array — pick the brightest color).
        try:
            ij = getattr(self.tif_slide, "imagej_metadata", None) or {}
            luts = ij.get("LUTs")
            if isinstance(luts, (list, tuple)) and len(luts) > 0:
                colors = []
                for i in range(num_channels):
                    if i < len(luts):
                        arr = np.asarray(luts[i])
                        if arr.shape == (3, 256):
                            # Top entry of each LUT row is the channel's display color.
                            colors.append((int(arr[0, -1]), int(arr[1, -1]), int(arr[2, -1])))
                            continue
                    colors.append(_DEFAULT_PALETTE[i % len(_DEFAULT_PALETTE)])
                return colors
        except Exception:
            pass

        # Fallback palette cycle.
        return [_DEFAULT_PALETTE[i % len(_DEFAULT_PALETTE)] for i in range(num_channels)]

    def __get_pixel_size_generic(self, keyframe):
        try:
            tags = keyframe.tags
            xres = tags.get("XResolution")
            yres = tags.get("YResolution")
            unit_tag = tags.get("ResolutionUnit")
            if xres is None or yres is None:
                raise ValueError("missing XResolution/YResolution")

            unit_value = int(getattr(unit_tag, "value", 2)) if unit_tag is not None else 2
            if unit_value == 2:
                unit_nm = 2.54e7  # 1 inch in nm
            elif unit_value == 3:
                unit_nm = 1e7  # 1 cm in nm
            else:
                raise ValueError(f"unsupported ResolutionUnit={unit_value}")

            x_pixels_per_unit = self.__rational_to_float(xres.value)
            y_pixels_per_unit = self.__rational_to_float(yres.value)
            if not x_pixels_per_unit or not y_pixels_per_unit:
                raise ValueError("zero resolution")

            return SlidePixelSizeNm(
                x=unit_nm / x_pixels_per_unit,
                y=unit_nm / y_pixels_per_unit,
            )
        except Exception as e:
            logger.warning("tifffile plugin: falling back to default pixel size (1 um/px): %s", e)
            return SlidePixelSizeNm(x=1000.0, y=1000.0)

    @staticmethod
    def __rational_to_float(value):
        if isinstance(value, (tuple, list)) and len(value) == 2:
            num, den = value
            if den == 0:
                return 0.0
            return float(num) / float(den)
        return float(value)
