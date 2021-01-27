import math

import openslide
import PIL
from fastapi import HTTPException

from wsi_service.models.slide import Extent, Level, PixelSizeNm, SlideInfo
from wsi_service.settings import Settings
from wsi_service.slide import Slide
from wsi_service.slide_utils import (
    check_generated_levels_for_originals,
    rgba_to_rgb_with_background_color,
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
        self.slide_info = self.get_slide_info(self.openslide_slide, slide_id)

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

    @staticmethod
    def calc_num_levels(openslide_slide):
        min_extent = min(openslide_slide.dimensions)
        return int(math.log2(min_extent) + 1)

    @staticmethod
    def get_original_levels(openslide_slide):
        levels = []
        for level in range(openslide_slide.level_count):
            levels.append(
                Level(
                    extent=Extent(
                        x=openslide_slide.level_dimensions[level][0],
                        y=openslide_slide.level_dimensions[level][1],
                        z=1,
                    ),
                    downsample_factor=openslide_slide.level_downsamples[level],
                    generated=False,
                )
            )
        return levels

    @staticmethod
    def get_generated_levels(openslide_slide, coarsest_native_level):
        levels = []
        for level in range(OpenSlideSlide.calc_num_levels(openslide_slide)):
            extent = Extent(
                x=openslide_slide.dimensions[0] / (2 ** level),
                y=openslide_slide.dimensions[1] / (2 ** level),
                z=1,
            )
            downsample_factor = 2 ** level
            if (
                downsample_factor > 4 * coarsest_native_level.downsample_factor
            ):  # only include levels up to two levels below coarsest native level
                continue
            levels.append(
                Level(
                    extent=extent,
                    downsample_factor=downsample_factor,
                    generated=True,
                )
            )
        return levels

    @staticmethod
    def get_levels(openslide_slide):
        original_levels = OpenSlideSlide.get_original_levels(openslide_slide)
        generated_levels = OpenSlideSlide.get_generated_levels(openslide_slide, original_levels[-1])
        check_generated_levels_for_originals(original_levels, generated_levels)
        return generated_levels

    @staticmethod
    def get_pixel_size(openslide_slide):
        if openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] == "generic-tiff":
            if openslide_slide.properties["tiff.ResolutionUnit"] == "centimeter":
                pixel_per_cm_x = float(openslide_slide.properties["tiff.XResolution"])
                pixel_per_cm_y = float(openslide_slide.properties["tiff.YResolution"])
                pixel_size_nm_x = 1e7 / pixel_per_cm_x
                pixel_size_nm_y = 1e7 / pixel_per_cm_y
            else:
                raise ("Unable to extract pixel size from metadata.")
        elif (
            openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] == "aperio"
            or openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] == "mirax"
            or openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] == "hamamatsu"
        ):
            pixel_size_nm_x = 1000.0 * float(openslide_slide.properties[openslide.PROPERTY_NAME_MPP_X])
            pixel_size_nm_y = 1000.0 * float(openslide_slide.properties[openslide.PROPERTY_NAME_MPP_Y])
        else:
            raise ("Unable to extract pixel size from metadata.")
        return PixelSizeNm(x=pixel_size_nm_x, y=pixel_size_nm_y)

    @staticmethod
    def get_tile_extent(openslide_slide):
        if (
            "openslide.level[0].tile-height" in openslide_slide.properties
            and "openslide.level[0].tile-width" in openslide_slide.properties
        ):
            tile_height = openslide_slide.properties["openslide.level[0].tile-height"]
            tile_width = openslide_slide.properties["openslide.level[0].tile-width"]
        else:
            tile_height = 256
            tile_width = 256
        return Extent(x=tile_width, y=tile_height, z=1)

    @staticmethod
    def get_slide_info(openslide_slide, slide_id):
        try:
            levels = OpenSlideSlide.get_levels(openslide_slide)
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to retireve slide level data. [{e}]",
            )
        try:
            slide_info = SlideInfo(
                id=slide_id,
                extent=Extent(x=openslide_slide.dimensions[0], y=openslide_slide.dimensions[1], z=1),
                pixel_size_nm=OpenSlideSlide.get_pixel_size(openslide_slide),
                tile_extent=OpenSlideSlide.get_tile_extent(openslide_slide),
                num_levels=len(levels),
                levels=levels,
            )
            return slide_info
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to gather slide infos. [{e}]",
            )
