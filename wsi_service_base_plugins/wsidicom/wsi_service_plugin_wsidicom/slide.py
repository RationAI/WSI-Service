from fastapi import HTTPException
from wsidicom import WsiDicom
from wsidicom.errors import WsiDicomNotFoundError

from wsi_service.models.v3.slide import SlideExtent, SlideInfo, SlidePixelSizeNm
from wsi_service.singletons import settings
from wsi_service.slide import Slide as BaseSlide
from wsi_service.utils.icc_profile import ICCProfile, ICCProfileError
from wsi_service.utils.image_utils import rgba_to_rgb_with_background_color
from wsi_service.utils.slide_utils import get_original_levels, get_rgb_channel_list


class Slide(BaseSlide):
    async def open(self, filepath):
        self.filepath = filepath
        await self.open_slide()
        self.slide_info = self.__get_slide_info_dicom()
        self._icc = ICCProfile()
        self._profile_data = False

    async def open_slide(self):
        try:
            self.dicom_slide = WsiDicom.open(self.filepath)
        except WsiDicomNotFoundError as e:
            raise HTTPException(status_code=500, detail=f"WsiDicomNotFoundError: {e}")

    async def close(self):
        self.dicom_slide.close()
        self._icc.free_cache()

    async def get_info(self):
        return self.slide_info

    async def get_region(self, level, start_x, start_y, size_x, size_y, padding_color=None, z=0,
                         icc_profile_intent: str = None, icc_profile_strict: bool = False):
        if padding_color is None:
            padding_color = settings.padding_color
        level_dicom = self.dicom_slide.levels[level].level
        level_location = (
            (int)(start_x),
            (int)(start_y),
        )
        img = self.dicom_slide.read_region(level_location, level_dicom, (size_x, size_y))

        if icc_profile_intent is not None:
            try:
                img = self._icc.process_pil_image(
                    img, self.__get_icc_bytes(), icc_profile_strict, icc_profile_intent, True
                )
            except ICCProfileError as e:
                raise HTTPException(status_code=e.payload["status_code"], detail=e.payload["detail"]) from e

        rgb_img = rgba_to_rgb_with_background_color(img, padding_color)
        return rgb_img

    async def get_thumbnail(self, max_x, max_y, icc_profile_intent: str = None, icc_profile_strict: bool = False):
        if not hasattr(self, "thumbnail"):
            self.thumbnail = await self.__get_thumbnail_dicom(settings.max_thumbnail_size, settings.max_thumbnail_size,
                                                              icc_profile_intent, icc_profile_strict)
        thumbnail = self.thumbnail.copy()
        thumbnail.thumbnail((max_x, max_y))
        return thumbnail

    async def get_label(self):
        try:
            return self.dicom_slide.read_label()
        except WsiDicomNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail="Label image does not exist.",
            ) from e

    async def get_macro(self, icc_profile_intent: str = None, icc_profile_strict: bool = False):
        try:
            macro_image_data = self.dicom_slide.read_overview()
            if icc_profile_intent is not None:
                macro_image_data = self._icc.process_pil_image(
                    macro_image_data, self.__get_icc_bytes(), icc_profile_strict, icc_profile_intent, False
                )
            return macro_image_data
        except ICCProfileError as e:
            raise HTTPException(status_code=e.payload["status_code"], detail=e.payload["detail"]) from e
        except WsiDicomNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail="Macro image does not exist.",
            ) from e

    async def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0,
                       icc_profile_intent: str = None, icc_profile_strict: bool = False):
        try:
            level_dicom = self.dicom_slide.levels[level].level
            tile = self.dicom_slide.read_tile(level_dicom, (tile_x, tile_y))
            if icc_profile_intent is not None:

                tile = self._icc.process_pil_image(
                    tile, self.__get_icc_bytes(), icc_profile_strict, icc_profile_intent, True
                )
            return rgba_to_rgb_with_background_color(tile, padding_color)
        except ICCProfileError as e:
            raise HTTPException(status_code=e.payload["status_code"], detail=e.payload["detail"]) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to extract tile from WSI.") from e

    async def get_icc_profile(self):
        return self._icc.get_for_payload(self.__get_icc_bytes())

    # private

    def __get_levels_dicom(self):
        levels = self.dicom_slide.levels

        level_count = len(levels)
        level_dimensions = []
        level_downsamples = []

        for level in levels:
            level_dimensions.append(level.size.to_tuple())
            level_downsamples.append(2**level.level)

        original_levels = get_original_levels(
            level_count=level_count,
            level_dimensions=level_dimensions,
            level_downsamples=level_downsamples,
        )
        return original_levels

    def __get_pixel_size(self):
        mpp = self.dicom_slide.levels.get_level(0).mpp
        return SlidePixelSizeNm(x=1000.0 * mpp.width, y=1000.0 * mpp.height)

    def __get_tile_extent(self):
        tile_height = 256
        tile_width = 256

        # some tiles can have an unequal tile height and width that can cause problems in the slide viewer
        # since the tile route is soley used for viewing, we provide the default tile width and height
        base_level = self.dicom_slide.levels.get_level(0)
        temp_height = base_level.tile_size.height
        temp_width = base_level.tile_size.width

        if temp_height == temp_width:
            tile_height = temp_height
            tile_width = temp_width

        return SlideExtent(x=tile_width, y=tile_height, z=1)

    def __get_slide_info_dicom(self):
        try:
            base_level = self.dicom_slide.levels.get_level(0)
            levels = self.__get_levels_dicom()
            slide_info = SlideInfo(
                id="",
                channels=get_rgb_channel_list(),  # rgb channels
                channel_depth=8,  # 8bit each channel
                extent=SlideExtent(
                    x=base_level.size.width,
                    y=base_level.size.height,
                    z=1,
                ),
                pixel_size_nm=self.__get_pixel_size(),
                tile_extent=self.__get_tile_extent(),
                num_levels=len(levels),
                levels=levels,
                format="dicom",
            )
            return slide_info
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Failed to gather slide infos. [{e}]")

    async def __get_thumbnail_dicom(self, max_x, max_y,
                                    icc_profile_intent: str = None,
                                    icc_profile_strict: bool = False):
        try:
            thumbnail = self.dicom_slide.read_thumbnail((max_x, max_y))
            if icc_profile_intent is not None:
                thumbnail = self._icc.process_pil_image(
                    thumbnail, self.__get_icc_bytes(), icc_profile_strict, icc_profile_intent, False
                )
            return thumbnail
        except ICCProfileError as e:
            raise HTTPException(status_code=e.payload["status_code"], detail=e.payload["detail"]) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to extract thumbnail from WSI.") from e

    def __get_icc_bytes(self):
        if self._profile_data is not False:
            return self._profile_data

        # For reference: using pydicom, it can be found like this
        # # Direct access does not work, can be nested, search
        # for elem in dataset.iterall():
        #     if elem.tag == Tag(0x0028, 0x2000):
        #         self._profile_data = elem.value

        self._profile_data = None

        # Todo: what is the correct optical path? E.g. fluorescence or z-stacks...
        for path in self.dicom_slide.metadata.optical_paths:
            if path.icc_profile:
                self._profile_data = path.icc_profile
                break
        return self._profile_data