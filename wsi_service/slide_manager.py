import atexit
import ctypes
import os
from threading import Lock, Timer

import requests
from fastapi import HTTPException

from wsi_service.plugins import load_slide


class ExpiringSlide:
    def __init__(self, slide, timer):
        self.slide = slide
        self.timer = timer


class SlideManager:
    def __init__(self, mapper_address, data_dir, timeout):
        atexit.register(self.close)
        self.lock = Lock()
        self.slide_map = {}  # maps from slide_id to storage
        self.opened_slides = {}
        self.mapper_address = mapper_address
        self.data_dir = data_dir
        self.timeout = timeout

    def close(self):
        for slide_id in list(self.opened_slides.keys()):
            self.opened_slides[slide_id].timer.cancel()
            self._close_slide(slide_id)

    def get_slide(self, slide_id):
        with self.lock:
            if slide_id not in self.opened_slides:
                self._map_slide(slide_id)
                filepath = os.path.join(self.data_dir, self.slide_map[slide_id]["address"])
                slide = load_slide(filepath, slide_id)
                if slide == None:
                    raise HTTPException(status_code=404, detail="No appropriate file format reader")
                try:
                    self.opened_slides[slide_id] = ExpiringSlide(slide, None)
                except KeyError:
                    raise HTTPException(status_code=404)
            self._reset_slide_expiration(slide_id)
            return self.opened_slides[slide_id].slide

    def _reset_slide_expiration(self, slide_id):
        expiring_slide = self.opened_slides[slide_id]
        if expiring_slide.timer is not None:
            expiring_slide.timer.cancel()
        expiring_slide.timer = Timer(self.timeout, self._close_slide, [slide_id])
        expiring_slide.timer.start()

    def _map_slide(self, slide_id):
        if slide_id not in self.slide_map:
            storage_address = self._get_slide_main_storage_address(slide_id)
            self.slide_map[slide_id] = storage_address

    def _get_slide_main_storage_address(self, slide_id):
        r = requests.get(self.mapper_address.format(slide_id=slide_id))
        slide = r.json()
        if "storage_addresses" not in slide:
            raise HTTPException(status_code=400, detail=f"Could not find storage addresses ({slide}).")
        for storage_address in slide["storage_addresses"]:
            if storage_address["main_address"]:
                return storage_address
        return slide["storage_addresses"][0]

    def _get_reference_count_slide(self, slide_id):
        return ctypes.c_long.from_address(id(self.opened_slides[slide_id].slide)).value

    def _close_slide(self, slide_id):
        with self.lock:
            if slide_id in self.opened_slides and slide_id in self.slide_map:
                if self._get_reference_count_slide(slide_id) == 1:
                    self.opened_slides[slide_id].slide.close()
                    del self.opened_slides[slide_id]
                    del self.slide_map[slide_id]
