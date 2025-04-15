import glob
import os

import openslide
from fastapi import HTTPException

from PIL import ImageCms

from wsi_service.models.v3.slide import SlideExtent, SlideInfo, SlidePixelSizeNm
from wsi_service.singletons import settings
from wsi_service.slide import Slide as BaseSlide
from wsi_service.utils.image_utils import rgba_to_rgb_with_background_color
from wsi_service.utils.slide_utils import get_original_levels, get_rgb_channel_list

class Slide(BaseSlide):
    supported_vendors = [
        "aperio",
        "mirax",
        "hamamatsu",
        "ventana",
        "leica",
        "trestle",
        "philips",
        "zeiss",
        "dicom"
    ]

    async def open(self, filepath):
        self.filepath = self.__check_and_adapt_filepath(filepath)
        await self.open_slide()
        self.format = self.slide.detect_format(self.filepath)
        self.slide_info = self.__get_slide_info_openslide()
        self.__transform = None

    async def open_slide(self):
        try:
            self.slide = openslide.OpenSlide(self.filepath)
        except openslide.OpenSlideError as e:
            raise HTTPException(status_code=500, detail=f"OpenSlideError: {e}")

    async def close(self):
        self.slide.close()

    async def get_info(self):
        return self.slide_info

    async def get_region(self, level, start_x, start_y, size_x, size_y, padding_color=None, z=0, icc_intent=None):
        if padding_color is None:
            padding_color = settings.padding_color
        downsample_factor = self.slide_info.levels[level].downsample_factor
        level_0_location = (
            (int)(start_x * downsample_factor),
            (int)(start_y * downsample_factor),
        )
        try:
            img = self.slide.read_region(level_0_location, level, (size_x, size_y))

            if not self.__transform:
                self.__transform = ImageCms.buildTransform(self.slide.color_profile,
                                                           ImageCms.createProfile('sRGB'), 'RGBA', 'RGBA')
            img = ImageCms.applyTransform(img, self.__transform)

        except openslide.OpenSlideError as e:
            raise HTTPException(status_code=500, detail=f"OpenSlideError: {e}")
        rgb_img = rgba_to_rgb_with_background_color(img, padding_color)
        return rgb_img

    async def get_thumbnail(self, max_x, max_y, icc_intent=None):
        # Todo: icc_intent not applied here and or macro, also not implemented in any other plugins
        if not hasattr(self, "thumbnail"):
            try:
                self.thumbnail = self.__get_associated_image("thumbnail")
            except HTTPException:
                self.thumbnail = await self.__get_thumbnail_openslide(
                    settings.max_thumbnail_size, settings.max_thumbnail_size, icc_intent
                )
        thumbnail = self.thumbnail.copy()
        thumbnail.thumbnail((max_x, max_y))
        return thumbnail

    async def get_label(self):
        return self.__get_associated_image("label")

    async def get_macro(self, icc_intent=None):
        return self.__get_associated_image("macro")

    async def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0, icc_intent=None):
        return await self.get_region(
            level,
            tile_x * self.slide_info.tile_extent.x,
            tile_y * self.slide_info.tile_extent.y,
            self.slide_info.tile_extent.x,
            self.slide_info.tile_extent.y,
            padding_color,
            icc_intent,
        )

    async def get_icc_profile(self):
        profile = self.slide.color_profile
        if profile:
            return profile.tobytes()

        raise HTTPException(404, "Icc profile not supported.")

    # private

    def __check_and_adapt_filepath(self, filepath):
        if os.path.isdir(filepath):
            # dir_files = glob.glob(os.path.join(filepath, "*.vsf"))
            dir_files = glob.glob(os.path.join(filepath, "*.dcm"))
            if len(dir_files) > 0:
                filepath = dir_files[0]
        return filepath

    def __get_associated_image(self, associated_image_name):
        if associated_image_name not in self.slide.associated_images:
            raise HTTPException(
                status_code=404,
                detail=f"Associated image {associated_image_name} does not exist.",
            )
        associated_image_rgba = self.slide.associated_images[associated_image_name]
        return associated_image_rgba.convert("RGB")

    def __get_levels_openslide(self):
        original_levels = get_original_levels(
            self.slide.level_count,
            self.slide.level_dimensions,
            self.slide.level_downsamples,
        )
        return original_levels

    def __get_pixel_size(self):
        if self.slide.properties[openslide.PROPERTY_NAME_VENDOR] == "generic-tiff":
            if self.slide.properties["tiff.ResolutionUnit"] == "centimeter":
                if "tiff.XResolution" not in self.slide.properties or "tiff.YResolution" not in self.slide.properties:
                    raise HTTPException(
                        status_code=404,
                        detail="Generic tiff file is missing valid values for x and y resolution.",
                    )
                pixel_per_cm_x = float(self.slide.properties["tiff.XResolution"])
                pixel_per_cm_y = float(self.slide.properties["tiff.YResolution"])
                pixel_size_nm_x = 1e7 / pixel_per_cm_x
                pixel_size_nm_y = 1e7 / pixel_per_cm_y
            else:
                raise HTTPException(
                    status_code=404,
                    detail="Unable to extract pixel size from metadata.",
                )
        elif self.slide.properties[openslide.PROPERTY_NAME_VENDOR] in self.supported_vendors:
            pixel_size_nm_x = 1000.0 * float(self.slide.properties[openslide.PROPERTY_NAME_MPP_X])
            pixel_size_nm_y = 1000.0 * float(self.slide.properties[openslide.PROPERTY_NAME_MPP_Y])
        else:
            raise HTTPException(
                status_code=404,
                detail="Unable to extract pixel size from metadata.",
            )
        return SlidePixelSizeNm(x=pixel_size_nm_x, y=pixel_size_nm_y)

    def __get_tile_extent(self):
        tile_height = 256
        tile_width = 256
        if (
            "openslide.level[0].tile-height" in self.slide.properties
            and "openslide.level[0].tile-width" in self.slide.properties
        ):
            # some tiles can have an unequal tile height and width that can cause problems in the slide viewer
            # since the tile route is used for viewing only, we provide the default tile width and height
            temp_height = self.slide.properties["openslide.level[0].tile-height"]
            temp_width = self.slide.properties["openslide.level[0].tile-width"]
            if temp_height == temp_width:
                tile_height = temp_height
                tile_width = temp_width
        return SlideExtent(x=tile_width, y=tile_height, z=1)

    def __get_slide_info_openslide(self):
        try:
            levels = self.__get_levels_openslide()
            slide_info = SlideInfo(
                id="",
                channels=get_rgb_channel_list(),  # rgb channels
                channel_depth=8,  # 8bit each channel
                extent=SlideExtent(
                    x=self.slide.dimensions[0],
                    y=self.slide.dimensions[1],
                    z=1,
                ),
                pixel_size_nm=self.__get_pixel_size(),
                tile_extent=self.__get_tile_extent(),
                num_levels=len(levels),
                levels=levels,
                format=self.format,
            )
            return slide_info
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Failed to gather slide infos. [{e}]")

    async def __get_thumbnail_openslide(self, max_x, max_y, icc_intent):
        level = self.__get_best_level_for_thumbnail(max_x, max_y)
        try:
            thumbnail = await self.get_region(
                level,
                0,
                0,
                self.slide_info.levels[level].extent.x,
                self.slide_info.levels[level].extent.y,
                icc_intent
            )
        except HTTPException as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract thumbnail from WSI [{e.detail}].",
            )
        thumbnail.thumbnail((max_x, max_y))
        return thumbnail

    def __get_best_level_for_thumbnail(self, max_x, max_y):
        best_level = 0
        for level in self.slide_info.levels:
            if level.extent.x < max_x and level.extent.y < max_y:
                return best_level - 1
            best_level += 1
        return best_level - 1
