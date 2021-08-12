import asyncio
import atexit
import os

import aiohttp
from fastapi import HTTPException

from wsi_service.plugins import load_slide


class ExpiringSlide:
    def __init__(self, slide, timer=None):
        self.slide = slide
        self.timer = timer


class SlideManager:
    def __init__(self, mapper_address, data_dir, timeout):
        self.mapper_address = mapper_address
        self.data_dir = data_dir
        self.timeout = timeout
        self.slide_map = {}
        self.opened_slides = {}
        self.lock = asyncio.Lock()
        self.slide_locks = {}
        self.event_loop = asyncio.get_event_loop()
        atexit.register(self.close)

    def close(self):
        for slide_id in list(self.opened_slides.keys()):
            self.opened_slides[slide_id].timer.cancel()
            self._close_slide(slide_id)

    async def get_slide(self, slide_id):
        if slide_id not in self.slide_locks:
            await self._set_slide_lock(slide_id)
        if slide_id not in self.opened_slides:
            async with self.slide_locks[slide_id]:
                await self._open_slide(slide_id)
        self._reset_slide_expiration(slide_id)
        return self.opened_slides[slide_id].slide

    async def _set_slide_lock(self, slide_id):
        async with self.lock:
            if slide_id not in self.slide_locks:
                self.slide_locks[slide_id] = asyncio.Lock()

    async def _open_slide(self, slide_id):
        if slide_id not in self.opened_slides:
            await self._map_slide(slide_id)
            filepath = os.path.join(self.data_dir, self.slide_map[slide_id]["address"])
            slide = await load_slide(filepath, slide_id)
            self.opened_slides[slide_id] = ExpiringSlide(slide)

    def _reset_slide_expiration(self, slide_id):
        expiring_slide = self.opened_slides[slide_id]
        if expiring_slide.timer is not None:
            expiring_slide.timer.cancel()
        expiring_slide.timer = self.event_loop.call_later(self.timeout, self._close_slide, slide_id)

    async def _map_slide(self, slide_id):
        if slide_id not in self.slide_map:
            storage_address = await self._get_slide_main_storage_address(slide_id)
            self.slide_map[slide_id] = storage_address

    async def _get_slide_main_storage_address(self, slide_id):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.mapper_address.format(slide_id=slide_id)) as r:
                    if r.status == 404:
                        raise HTTPException(
                            status_code=404, detail=f"Could not find a storage address for slide id {slide_id}."
                        )
                    slide = await r.json()
        except aiohttp.ClientConnectorError:
            raise HTTPException(
                status_code=503, detail="WSI Service is unable to connect to the Storage Mapper Service."
            )
        for storage_address in slide["storage_addresses"]:
            if storage_address["main_address"]:
                return storage_address
        return slide["storage_addresses"][0]

    def _close_slide(self, slide_id):
        if slide_id in self.opened_slides:
            self.opened_slides[slide_id].slide.close()
            del self.opened_slides[slide_id]
