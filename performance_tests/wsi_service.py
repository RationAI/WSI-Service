import io

import requests
from PIL import Image


class WSIService:
    def __init__(self, host="http://localhost:8080"):
        self.host = host

    def get_cases(self):
        r = requests.get(self.host + f"/v1/cases")
        assert r.status_code == 200
        return r.json()

    def get_slide(self, slide_id):
        r = requests.get(self.host + f"/v1/slides/{slide_id}")
        assert r.status_code == 200
        return r.json()

    def get_info(self, slide_id):
        r = requests.get(self.host + f"/v1/slides/{slide_id}/info")
        assert r.status_code == 200
        return r.json()

    def get_region(
        self,
        slide_id,
        level,
        start_x,
        start_y,
        size_x,
        size_y,
        params={"image_format": "jpg", "image_quality": 90, "z": 0},
    ):
        r = requests.get(
            self.host + f"/v1/slides/{slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}",
            stream=True,
            params=params,
        )
        assert r.status_code == 200
        image_bytes = io.BytesIO(r.content)
        img = Image.open(image_bytes)
        img.load()
        return len(r.content)

    def get_tile(self, slide_id, level, tile_x, tile_y, params={"image_format": "jpg", "image_quality": 90, "z": 0}):
        r = requests.get(
            self.host + f"/v1/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}", stream=True, params=params
        )
        assert r.status_code == 200
        image_bytes = io.BytesIO(r.content)
        img = Image.open(image_bytes)
        img.load()
        return len(r.content)
