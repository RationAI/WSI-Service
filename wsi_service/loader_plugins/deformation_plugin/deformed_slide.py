import io
import math

import PIL
import requests
import wsi_service.slide_utils
from PIL import Image
from wsi_service.image_utils import rgba_to_rgb_with_background_color
from wsi_service.loader_plugins.deformation_plugin.deformation_plugin import Deformation
from wsi_service.models.slide import SlideInfo
from wsi_service.slide import Slide
from wsi_service.slide_utils import Channel, Extent, Level, PixelSizeNm


class DeformedSlide(Slide):
    loader_name = "DeformedSlide"

    def __init__(self, filepath, slide_id):
        self.wsi_service_address = "http://localhost:8080"
        self.deformation = Deformation(filepath, self.wsi_service_address)
        self._slides = self.deformation.get_slide_ids()

        self.slide_info = self._get_slide_info_from_reference()

    def _get_slide_info_from_reference(self):
        slide_id = self._slides[0]
        r = requests.get(
            self.wsi_service_address + f"/v1/slides/{slide_id}/info",
        )
        assert r.status_code == 200
        slide_info = SlideInfo.parse_raw(r.content)
        return slide_info

    def get_info(self):
        return self.slide_info

    def get_region(self, level, start_x, start_y, size_x, size_y, z=0):
        return self.deformation.get_region(level, start_x, start_y, size_x, size_y, z, image_format="png")

    def get_thumbnail(self, max_x, max_y):
        slide_id = self._slides[0]
        r = requests.get(
            self.wsi_service_address + f"/v1/slides/{slide_id}/thumbnail/max_size/{max_x}/{max_y}",
        )
        assert r.status_code == 200
        image_bytes = io.BytesIO(r.content)
        img_rgb = Image.open(image_bytes)
        img_rgb.load()
        return img_rgb

    def get_label(self):
        slide_id = self._slides[0]
        r = requests.get(
            self.wsi_service_address + f"/v1/slides/{slide_id}/label",
        )
        assert r.status_code == 200
        image_bytes = io.BytesIO(r.content)
        img_rgb = Image.open(image_bytes)
        img_rgb.load()
        return img_rgb

    def get_macro(self):
        slide_id = self._slides[0]
        r = requests.get(
            self.wsi_service_address + f"/v1/slides/{slide_id}/macro",
        )
        assert r.status_code == 200
        image_bytes = io.BytesIO(r.content)
        img_rgb = Image.open(image_bytes)
        img_rgb.load()
        return img_rgb

    def __get_rgb_channel_list(self):
        channels = []
        channels.append(Channel(id=0, name="Red", color_int=16711680))
        channels.append(Channel(id=1, name="Green", color_int=65280))
        channels.append(Channel(id=2, name="Blue", color_int=255))
        return channels

    def close(self):
        pass  # we let the dependent slides expire.
