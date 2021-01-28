import math

import openslide
import PIL
from fastapi import HTTPException

from wsi_service.image_utils import rgba_to_rgb_with_background_color
from wsi_service.models.slide import Channel, Extent, Level, PixelSizeNm, SlideInfo
from wsi_service.settings import Settings
from wsi_service.slide import Slide
from wsi_service.slide_utils import (
    check_generated_levels_for_originals,
    get_generated_levels,
    get_original_levels,
)


class OpenSlideSlide(Slide):
    supported_file_types = ["mrxs", "tiff", "ndpi", "svs"]
    loader_name = "OpenSlide"

    def __init__(self, filepath, slide_id):
        try:
            self.openslide_slide = openslide.OpenSlide(filepath)
        except openslide.OpenSlideError as e:
            raise HTTPException(
                status_code=422,
                detail=f"OpenSlideError: {e}",
            )
        self.slide_info = self.__get_slide_info_openslide(slide_id)

    def close(self):
        self.openslide_slide.close()

    def get_info(self):
        return self.slide_info

    def get_region(self, level, start_x, start_y, size_x, size_y):
        settings = Settings()
        try:
            downsample_factor = int(self.slide_info.levels[level].downsample_factor)
        except IndexError:
            raise HTTPException(
                status_code=422,
                detail=f"""The requested pyramid level is not available. 
                    The coarsest available level is {len(self.slide_info.levels) - 1}.""",
            )
        base_level = self.openslide_slide.get_best_level_for_downsample(downsample_factor)
        if base_level >= len(self.openslide_slide.level_downsamples):
            raise HTTPException(
                status_code=422,
                detail=f"Downsample layer for requested base level {base_level} not available.",
            )
        remaining_downsample_factor = downsample_factor / self.openslide_slide.level_downsamples[base_level]
        base_size = (
            round(size_x * remaining_downsample_factor),
            round(size_y * remaining_downsample_factor),
        )
        level_0_location = (start_x * downsample_factor, start_y * downsample_factor)
        if base_size[0] * base_size[1] > settings.max_returned_region_size:
            raise HTTPException(
                status_code=403,
                detail=f"""Requested image region is too large. Maximum number of pixels is set to 
                    {settings.max_returned_region_size}, your request is for {base_size[0] * base_size[1]} pixels.""",
            )
        try:
            base_img = self.openslide_slide.read_region(level_0_location, base_level, base_size)
            rgba_img = base_img.resize((size_x, size_y), resample=PIL.Image.BILINEAR, reducing_gap=1.0)
            rgb_img = rgba_to_rgb_with_background_color(rgba_img)
        except openslide.OpenSlideError as e:
            raise HTTPException(
                status_code=422,
                detail=f"OpenSlideError: {e}",
            )

        return rgb_img

    def get_thumbnail(self, max_x, max_y):
        return self.openslide_slide.get_thumbnail((max_x, max_y))

    def _get_associated_image(self, associated_image_name):
        if associated_image_name not in self.openslide_slide.associated_images:
            raise HTTPException(
                status_code=404,
                detail=f"Associated image {associated_image_name} does not exist.",
            )
        associated_image_rgba = self.openslide_slide.associated_images[associated_image_name]
        return associated_image_rgba.convert("RGB")

    def get_label(self):
        return self._get_associated_image("label")

    def get_macro(self):
        return self._get_associated_image("macro")

    def get_tile(self, level, tile_x, tile_y):
        return self.get_region(
            level,
            tile_x * self.slide_info.tile_extent.x,
            tile_y * self.slide_info.tile_extent.y,
            self.slide_info.tile_extent.x,
            self.slide_info.tile_extent.y,
        )

    # private members

    def __get_levels_openslide(self):
        original_levels = get_original_levels(
            self.openslide_slide.level_count,
            self.openslide_slide.level_dimensions,
            self.openslide_slide.level_downsamples,
        )
        generated_levels = get_generated_levels(self.openslide_slide.dimensions, original_levels[-1])
        check_generated_levels_for_originals(original_levels, generated_levels)
        return generated_levels

    def __get_pixel_size(self):
        if self.openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] == "generic-tiff":
            if self.openslide_slide.properties["tiff.ResolutionUnit"] == "centimeter":
                pixel_per_cm_x = float(self.openslide_slide.properties["tiff.XResolution"])
                pixel_per_cm_y = float(self.openslide_slide.properties["tiff.YResolution"])
                pixel_size_nm_x = 1e8 / pixel_per_cm_x
                pixel_size_nm_y = 1e8 / pixel_per_cm_y
            else:
                raise ("Unable to extract pixel size from metadata.")
        elif (
            self.openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] == "aperio"
            or self.openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] == "mirax"
            or self.openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] == "hamamatsu"
        ):
            pixel_size_nm_x = 1000.0 * float(self.openslide_slide.properties[openslide.PROPERTY_NAME_MPP_X])
            pixel_size_nm_y = 1000.0 * float(self.openslide_slide.properties[openslide.PROPERTY_NAME_MPP_Y])
        else:
            raise ("Unable to extract pixel size from metadata.")
        return PixelSizeNm(x=pixel_size_nm_x, y=pixel_size_nm_y)

    def __get_tile_extent(self):
        if (
            "openslide.level[0].tile-height" in self.openslide_slide.properties
            and "openslide.level[0].tile-width" in self.openslide_slide.properties
        ):
            tile_height = self.openslide_slide.properties["openslide.level[0].tile-height"]
            tile_width = self.openslide_slide.properties["openslide.level[0].tile-width"]
        else:
            tile_height = 256
            tile_width = 256
        return Extent(x=tile_width, y=tile_height, z=1)

    def __get_rgb_channel_list(self):
        channels = []
        channels.append(Channel(id=0, name="Red", color_int=16711680))
        channels.append(Channel(id=1, name="Green", color_int=65280))
        channels.append(Channel(id=2, name="Blue", color_int=255))
        return channels

    def __get_slide_info_openslide(self, slide_id):
        try:
            levels = self.__get_levels_openslide()
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to retrieve slide level data. [{e}]",
            )
        try:
            slide_info = SlideInfo(
                id=slide_id,
                channels=self.__get_rgb_channel_list(),  # rgb channels
                channel_depth=8,  # 8bit each channel
                extent=Extent(x=self.openslide_slide.dimensions[0], y=self.openslide_slide.dimensions[1], z=1),
                pixel_size_nm=self.__get_pixel_size(),
                tile_extent=self.__get_tile_extent(),
                num_levels=len(levels),
                levels=levels,
            )
            return slide_info
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to gather slide infos. [{e}]",
            )
