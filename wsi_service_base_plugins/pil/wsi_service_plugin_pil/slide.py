from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from wsi_service.models.slide import SlideChannel, SlideColor, SlideExtent, SlideInfo, SlideLevel, SlidePixelSizeNm
from wsi_service.slide import Slide as BaseSlide


class Slide(BaseSlide):
    def __init__(self, filepath, slide_id):
        try:
            self.slide_image = Image.open(filepath)
        except UnidentifiedImageError:
            raise HTTPException(status_code=422, detail="PIL Unidentified Image Error")
        self.slide_image = Image.open(filepath)
        width, height = self.slide_image.size
        channels = []
        channels.append(SlideChannel(id=0, name="Red", color=SlideColor(r=255, g=0, b=0, a=0)))
        channels.append(SlideChannel(id=1, name="Green", color=SlideColor(r=0, g=255, b=0, a=0)))
        channels.append(SlideChannel(id=2, name="Blue", color=SlideColor(r=0, g=0, b=255, a=0)))
        self.slide_info = SlideInfo(
            id=slide_id,
            channels=channels,
            channel_depth=8,
            extent=SlideExtent(x=width, y=height, z=1),
            num_levels=1,
            pixel_size_nm=SlidePixelSizeNm(x=0, y=0),  # pixel size unknown
            tile_extent=SlideExtent(x=width, y=height, z=1),
            levels=[SlideLevel(extent=SlideExtent(x=width, y=height, z=1), downsample_factor=1.0)],
        )

    def close(self):
        self.slide_image.close()

    def get_info(self):
        return self.slide_info

    def get_region(self, level, start_x, start_y, size_x, size_y, padding_color=None, z=0):
        if level != 0:
            raise HTTPException(
                status_code=422,
                detail=f"""The requested pyramid level is not available. 
                    The coarsest available level is {len(self.slide_info.levels) - 1}.""",
            )
        return self.slide_image.crop((start_x, start_y, size_x, size_y))

    def get_thumbnail(self, max_x, max_y):
        thumbnail = self.slide_image.copy()
        thumbnail.thumbnail((max_x, max_y))
        return thumbnail

    def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0):
        return self.get_region(
            level,
            tile_x * self.slide_info.tile_extent.x,
            tile_y * self.slide_info.tile_extent.y,
            self.slide_info.tile_extent.x,
            self.slide_info.tile_extent.y,
            z=z,
        )

    def _get_associated_image(self, associated_image_name):
        raise HTTPException(
            status_code=404,
            detail=f"Associated image {associated_image_name} does not exist.",
        )

    def get_label(self):
        self._get_associated_image("label")

    def get_macro(self):
        self._get_associated_image("macro")
