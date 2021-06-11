import importlib
from io import BytesIO

import zmq
from fastapi import HTTPException
from PIL import Image

from wsi_service.models.slide import (
    SlideExtent,
    SlideInfo,
    SlideLevel,
    SlidePixelSizeNm,
)
from wsi_service.singletons import settings
from wsi_service.slide import Slide
from wsi_service.slide_utils import get_rgb_channel_list


class IsyntaxSlide(Slide):
    loader_name = "IsyntaxSlide"
    port = 5556

    def __init__(self, filepath, slide_id):
        self.filepath = filepath
        self.slide_id = slide_id
        self.port = settings.isyntax_port

        # we need to remove the local data dir from our filename because the local
        # dir is mapped to /data in isyntax-backend container
        if filepath.startswith("/data"):
            self.filepath = filepath.replace("/data", "")

        socket = self.__get_new_context_socket()
        req = {"req": "verification", "filepath": self.filepath, "slide_id": slide_id}
        socket.send_json(req)

        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        if poller.poll(2 * 1000):  # 2s timeout
            verification = socket.recv_json()
            if verification["status_code"] != 200:
                raise HTTPException(status_code=verification["status_code"], detail=verification["detail"])
        else:
            raise HTTPException(status_code=408, detail="Pyzmq request timeout. Could not reach isyntax backend.")

    def close(self):
        self.filepath = None
        self.slide_id = None

    def get_info(self):
        socket = self.__get_new_context_socket()
        req = {"req": "get_info", "filepath": self.filepath, "slide_id": self.slide_id}
        socket.send_json(req)
        info = socket.recv_json()
        return self.__parse_info_reply(info)

    def get_region(self, level, start_x, start_y, size_x, size_y):
        socket = self.__get_new_context_socket()
        req = {
            "req": "get_region",
            "filepath": self.filepath,
            "slide_id": self.slide_id,
            "level": level,
            "start_x": start_x,
            "start_y": start_y,
            "size_x": size_x,
            "size_y": size_y,
        }

        socket.send_json(req)
        data = socket.recv_json()
        image_array = socket.recv()
        if data["rep"] == "success":
            image = Image.frombuffer("RGB", (data["width"], data["height"]), image_array, "raw", "RGB", 0, 1)
            image = image.resize((data["width"] - 1, data["height"] - 1), Image.ANTIALIAS)
            return image
        else:
            raise HTTPException(status_code=data["status_code"], detail=data["details"])

    def get_thumbnail(self, max_x, max_y):
        socket = self.__get_new_context_socket()
        req = {
            "req": "get_thumbnail",
            "filepath": self.filepath,
            "slide_id": self.slide_id,
            "max_x": max_x,
            "max_y": max_y,
        }

        socket.send_json(req)
        data = socket.recv_json()
        image_array = socket.recv()
        if data["rep"] == "success":
            image = Image.frombuffer("RGB", (data["width"], data["height"]), image_array, "raw", "RGB", 0, 1)
            image.thumbnail((max_x, max_y), resample=Image.ANTIALIAS)
            return image
        else:
            raise HTTPException(status_code=data["status_code"], detail=data["details"])

    def _get_associated_image(self, associated_image_name):
        socket = self.__get_new_context_socket()
        req = {"req": associated_image_name, "filepath": self.filepath, "slide_id": self.slide_id}
        socket.send_json(req)
        image_data = socket.recv()
        return Image.open(BytesIO(image_data))

    def get_label(self):
        return self._get_associated_image("LABEL")

    def get_macro(self):
        return self._get_associated_image("MACRO")

    def get_tile(self, level, tile_x, tile_y):
        socket = self.__get_new_context_socket()
        req = {
            "req": "get_tile",
            "filepath": self.filepath,
            "slide_id": self.slide_id,
            "level": level,
            "tile_x": tile_x,
            "tile_y": tile_y,
        }

        socket.send_json(req)
        data = socket.recv_json()
        image_array = socket.recv()
        if data["rep"] == "success":
            image = Image.frombuffer("RGB", (data["width"], data["height"]), image_array, "raw", "RGB", 0, 1)
            image = image.resize((data["width"] - 1, data["height"] - 1), Image.ANTIALIAS)
            return image
        else:
            raise HTTPException(status_code=data["status_code"], detail=data["details"])

    # private member

    def __get_new_context_socket(self):
        context = zmq.Context()
        socket = context.socket(zmq.REQ)  # pylint: disable=no-member
        socket.setsockopt(zmq.LINGER, 1)
        socket.connect(f"tcp://isyntax-backend:{self.port}")
        return socket

    def __parse_levels(self, info):
        levels = []
        for level in info["levels"]:
            levels.append(
                SlideLevel(
                    extent=SlideExtent(x=level["extent"]["x"], y=level["extent"]["y"], z=level["extent"]["z"]),
                    downsample_factor=level["downsample_factor"],
                )
            )
        return levels

    def __parse_info_reply(self, info):
        levels = self.__parse_levels(info)
        slide_info_obj = SlideInfo(
            id=info["id"],
            channels=get_rgb_channel_list(),  # rgb channels
            channel_depth=8,  # 8bit each channel
            extent=SlideExtent(x=info["extent"]["x"], y=info["extent"]["y"], z=info["extent"]["z"]),
            pixel_size_nm=SlidePixelSizeNm(x=info["pixel_size_nm"][0], y=info["pixel_size_nm"][1], z=0),
            tile_extent=SlideExtent(x=info["tile_extent"]["x"], y=info["tile_extent"]["y"], z=info["tile_extent"]["z"]),
            num_levels=len(levels),
            levels=levels,
        )
        return slide_info_obj
