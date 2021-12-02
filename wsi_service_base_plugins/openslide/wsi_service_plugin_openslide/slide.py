import openslide
from fastapi import HTTPException

from wsi_service.image_utils import rgba_to_rgb_with_background_color
from wsi_service.models.slide import SlideExtent, SlideInfo, SlidePixelSizeNm
from wsi_service.singletons import settings
from wsi_service.slide import Slide as BaseSlide
from wsi_service.slide_utils import get_original_levels, get_rgb_channel_list


class Slide(BaseSlide):
    supported_vendors = [
        "aperio",
        "mirax",
        "hamamatsu",
        "ventana",
        "leica",
        "trestle",
        "philips",
    ]

    async def open(self, filepath):
        await self.open_slide()
        self.slide_info = self.__get_slide_info_openslide()
        self.thumbnail = await self.__get_thumbnail_openslide(settings.max_thumbnail_size, settings.max_thumbnail_size)
        await self.close()
        await self.open_slide()

    async def open_slide(self):
        try:
            self.openslide_slide = openslide.OpenSlide(self.filepath)
        except openslide.OpenSlideError as e:
            raise HTTPException(status_code=422, detail=f"OpenSlideError: {e}")

    async def close(self):
        self.openslide_slide.close()

    async def get_info(self):
        return self.slide_info

    async def get_region(self, level, start_x, start_y, size_x, size_y, padding_color=None, z=0):
        if padding_color is None:
            padding_color = settings.padding_color
        try:
            downsample_factor = self.slide_info.levels[level].downsample_factor
        except IndexError:
            raise HTTPException(
                status_code=422,
                detail=f"""The requested pyramid level is not available. 
                    The coarsest available level is {len(self.slide_info.levels) - 1}.""",
            )
        base_level = level
        if base_level >= len(self.openslide_slide.level_downsamples):
            raise HTTPException(
                status_code=422,
                detail=f"Downsample layer for requested base level {base_level} not available.",
            )
        base_size = (size_x, size_y)
        level_0_location = (
            (int)(start_x * downsample_factor),
            (int)(start_y * downsample_factor),
        )
        if base_size[0] * base_size[1] > settings.max_returned_region_size:
            raise HTTPException(
                status_code=403,
                detail=f"""Requested image region is too large. Maximum number of pixels is set to 
                    {settings.max_returned_region_size}, your request is for {base_size[0] * base_size[1]} pixels.""",
            )
        try:
            base_img = self.openslide_slide.read_region(level_0_location, base_level, base_size)
            rgb_img = rgba_to_rgb_with_background_color(base_img, padding_color)
        except openslide.OpenSlideError as e:
            raise HTTPException(status_code=422, detail=f"OpenSlideError: {e}")

        return rgb_img

    async def get_thumbnail(self, max_x, max_y):
        thumbnail = self.thumbnail.copy()
        thumbnail.thumbnail((max_x, max_y))
        return thumbnail

    async def get_label(self):
        return self._get_associated_image("label")

    async def get_macro(self):
        return self._get_associated_image("macro")

    async def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0):
        return await self.get_region(
            level,
            tile_x * self.slide_info.tile_extent.x,
            tile_y * self.slide_info.tile_extent.y,
            self.slide_info.tile_extent.x,
            self.slide_info.tile_extent.y,
            padding_color,
        )

    # private members

    def _get_associated_image(self, associated_image_name):
        if associated_image_name not in self.openslide_slide.associated_images:
            raise HTTPException(
                status_code=404,
                detail=f"Associated image {associated_image_name} does not exist.",
            )
        associated_image_rgba = self.openslide_slide.associated_images[associated_image_name]
        return associated_image_rgba.convert("RGB")

    def __get_levels_openslide(self):
        original_levels = get_original_levels(
            self.openslide_slide.level_count,
            self.openslide_slide.level_dimensions,
            self.openslide_slide.level_downsamples,
        )
        return original_levels

    def __get_pixel_size(self):
        if self.openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] == "generic-tiff":
            if self.openslide_slide.properties["tiff.ResolutionUnit"] == "centimeter":
                pixel_per_cm_x = float(self.openslide_slide.properties["tiff.XResolution"])
                pixel_per_cm_y = float(self.openslide_slide.properties["tiff.YResolution"])
                pixel_size_nm_x = 1e7 / pixel_per_cm_x
                pixel_size_nm_y = 1e7 / pixel_per_cm_y
            else:
                raise ("Unable to extract pixel size from metadata.")
        elif self.openslide_slide.properties[openslide.PROPERTY_NAME_VENDOR] in self.supported_vendors:
            pixel_size_nm_x = 1000.0 * float(self.openslide_slide.properties[openslide.PROPERTY_NAME_MPP_X])
            pixel_size_nm_y = 1000.0 * float(self.openslide_slide.properties[openslide.PROPERTY_NAME_MPP_Y])
        else:
            raise ("Unable to extract pixel size from metadata.")
        return SlidePixelSizeNm(x=pixel_size_nm_x, y=pixel_size_nm_y)

    def __get_tile_extent(self):
        tile_height = 256
        tile_width = 256
        if (
            "openslide.level[0].tile-height" in self.openslide_slide.properties
            and "openslide.level[0].tile-width" in self.openslide_slide.properties
        ):
            # some tiles can have an unequal tile height and width that can cause problems in the slide viewer
            # since the tile route is soley used for viewing, we provide the default tile width and height
            temp_height = self.openslide_slide.properties["openslide.level[0].tile-height"]
            temp_width = self.openslide_slide.properties["openslide.level[0].tile-width"]
            if temp_height == temp_width:
                tile_height = temp_height
                tile_width = temp_width

        return SlideExtent(x=tile_width, y=tile_height, z=1)

    def __get_slide_info_openslide(self):
        try:
            levels = self.__get_levels_openslide()
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Failed to retrieve slide level data. [{e}]")
        try:
            slide_info = SlideInfo(
                id="",
                channels=get_rgb_channel_list(),  # rgb channels
                channel_depth=8,  # 8bit each channel
                extent=SlideExtent(
                    x=self.openslide_slide.dimensions[0],
                    y=self.openslide_slide.dimensions[1],
                    z=1,
                ),
                pixel_size_nm=self.__get_pixel_size(),
                tile_extent=self.__get_tile_extent(),
                num_levels=len(levels),
                levels=levels,
            )
            return slide_info
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Failed to gather slide infos. [{e}]")

    async def __get_thumbnail_openslide(self, max_x, max_y):
        level = self.__get_best_level_for_thumbnail(max_x, max_y)
        thumbnail = await self.get_region(
            level,
            0,
            0,
            self.slide_info.levels[level].extent.x,
            self.slide_info.levels[level].extent.y,
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
