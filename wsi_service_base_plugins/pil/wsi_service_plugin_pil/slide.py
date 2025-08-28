from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from wsi_service.models.v3.slide import SlideExtent, SlideInfo, SlideLevel, SlidePixelSizeNm
from wsi_service.singletons import settings
from wsi_service.slide import Slide as BaseSlide
from wsi_service.utils.icc_profile import ICCProfileError, ICCProfile
from wsi_service.utils.slide_utils import get_rgb_channel_list


class Slide(BaseSlide):
    async def open(self, filepath):
        try:
            self.slide_image = Image.open(filepath)
        except UnidentifiedImageError:
            raise HTTPException(status_code=500, detail="PIL Unidentified Image Error")
        self.slide_image = Image.open(filepath).convert("RGB")
        width, height = self.slide_image.size
        self._icc = ICCProfile()

        channels = get_rgb_channel_list()
        self.slide_info = SlideInfo(
            id="",
            channels=channels,
            channel_depth=8,
            extent=SlideExtent(x=width, y=height, z=1),
            num_levels=1,
            pixel_size_nm=SlidePixelSizeNm(x=-1, y=-1),  # pixel size unknown
            tile_extent=SlideExtent(x=width, y=height, z=1) if width < 5000 and height < 5000 else SlideExtent(x=1024, y=1024, z=1),
            levels=[SlideLevel(extent=SlideExtent(x=width, y=height, z=1), downsample_factor=1.0)],
        )

    async def close(self):
        self.slide_image.close()
        self._icc.free_cache()

    async def get_info(self):
        return self.slide_info

    async def get_region(self, level, start_x, start_y, size_x, size_y, padding_color=None, z=0,
                         icc_profile_intent: str = None, icc_profile_strict: bool = False):
        if padding_color is None:
            padding_color = settings.padding_color
        region = self.slide_image.crop(
            (
                start_x,
                start_y,
                start_x + size_x,
                start_y + size_y,
            )
        )

        if icc_profile_intent is not None:
            try:
                profile = self.slide_image.info.get("icc_profile")
                region = self._icc.process_pil_image(
                    region, profile, icc_profile_strict, icc_profile_intent, True
                )
            except ICCProfileError as e:
                raise HTTPException(status_code=e.payload["status_code"], detail=e.payload["detail"]) from e

        return region

    async def get_thumbnail(self, max_x, max_y, icc_profile_intent: str = None, icc_profile_strict: bool = False):
        thumbnail = self.slide_image.copy()
        thumbnail.thumbnail((max_x, max_y))
        if icc_profile_intent is not None:
            try:
                profile = self.slide_image.info.get("icc_profile")
                thumbnail = self._icc.process_pil_image(
                    thumbnail, profile, icc_profile_strict, icc_profile_intent, True
                )
            except ICCProfileError as e:
                raise HTTPException(status_code=e.payload["status_code"], detail=e.payload["detail"]) from e
        return thumbnail

    async def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0, icc_profile_intent: str = None,
                       icc_profile_strict: bool = False):
        return await self.get_region(
            level,
            tile_x * self.slide_info.tile_extent.x,
            tile_y * self.slide_info.tile_extent.y,
            self.slide_info.tile_extent.x,
            self.slide_info.tile_extent.y,
            padding_color=padding_color,
            z=z,
            icc_profile_intent=icc_profile_intent,
            icc_profile_strict=icc_profile_strict,
        )

    async def get_label(self):
        self._get_associated_image("label")

    async def get_macro(self, icc_profile_intent: str = None, icc_profile_strict: bool = False):
        self._get_associated_image("macro")

    async def get_icc_profile(self):
        return self._icc.get_for_payload(self.slide_image.info.get("icc_profile", None))

    # private

    def _get_associated_image(self, associated_image_name):
        raise HTTPException(
            status_code=404,
            detail=f"Associated image {associated_image_name} does not exist.",
        )