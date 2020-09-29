import atexit
import os
from threading import Lock, Timer

from fastapi import HTTPException
from openslide import OpenSlide
import requests

from wsi_service.slide import Slide


class ExpiringSlide:
    def __init__(self, slide, timer):
        self.slide = slide
        self.timer = timer


class SlideSource:
    def __init__(self, mapper_address, data_dir, timeout):
        atexit.register(self.close)
        self.lock = Lock()
        self.slide_map = {} # maps from global_slide_id to storage
        self.opened_slides = {}
        self.mapper_address = mapper_address
        self.data_dir = data_dir
        self.timeout = timeout

    def close(self):
        for global_slide_id in list(self.opened_slides.keys()):
            self.opened_slides[global_slide_id].timer.cancel()
            self._close_slide(global_slide_id)

    def get_slide(self, global_slide_id):
        with self.lock:
            if not global_slide_id in self.opened_slides:
                try:
                    self._map_slide(global_slide_id)
                    filepath = os.path.join(self.data_dir, self.slide_map[global_slide_id]['storage_address'])
                    slide = Slide(OpenSlide(filepath))
                    self.opened_slides[global_slide_id] = ExpiringSlide(slide, None)
                except KeyError:
                    raise HTTPException(status_code=400)
            self._reset_slide_expiration(global_slide_id)
        return self.opened_slides[global_slide_id].slide

    def _reset_slide_expiration(self, global_slide_id):
        expiring_slide = self.opened_slides[global_slide_id]
        if expiring_slide.timer is not None:
            expiring_slide.timer.cancel()
        expiring_slide.timer = Timer(self.timeout, self._close_slide, [global_slide_id])
        expiring_slide.timer.start()

    def _map_slide(self, global_slide_id):
        slide = self._get_slide(global_slide_id)
        if global_slide_id not in self.slide_map:
            self.slide_map[global_slide_id] = slide
    
    def _get_slide(self, global_slide_id):
        r = requests.get(self.mapper_address.format(global_slide_id=global_slide_id))
        return r.json()

    def _close_slide(self, global_slide_id):
        with self.lock:
            if global_slide_id in self.opened_slides:
                self.opened_slides[global_slide_id].slide.close()
                del self.opened_slides[global_slide_id]
