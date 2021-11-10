import asyncio
import atexit
import os

import aiohttp
from fastapi import HTTPException

from wsi_service.plugins import load_slide

from .singletons import logger


class ExpiringSlide:
    def __init__(self, slide, timer=None):
        self.slide = slide
        self.timer = timer


class SlideManager:
    def __init__(self, mapper_address, data_dir, timeout):
        self.mapper_address = mapper_address
        self.data_dir = data_dir
        self.timeout = timeout
        self.opened_slide_storages = {}
        self.lock = asyncio.Lock()
        self.storage_locks = {}
        self.event_loop = asyncio.get_event_loop()
        atexit.register(self.close)

    def close(self):
        for storage_address in list(self.opened_slide_storages.keys()):
            self.opened_slide_storages[storage_address].timer.cancel()
            self._close_slide(storage_address)

    async def get_slide(self, slide_id):
        main_storage_address = await self._get_slide_main_storage_address(slide_id)
        storage_address = os.path.join(self.data_dir, main_storage_address["address"])
        logger.debug("Get slide %s at storage address: %s", slide_id, storage_address)

        await self._set_storage_lock(storage_address)

        if storage_address not in self.opened_slide_storages:
            logger.debug("Open new slide for ID: %s and storage address: %s.", slide_id, storage_address)
            async with self.storage_locks[storage_address]:
                await self._open_slide(storage_address, slide_id)
        else:
            logger.debug("Slide %s is already open.", slide_id)

        self._reset_slide_expiration(storage_address)

        try:  # check if slide is up-to-date (and update) if supported
            await self.opened_slide_storages[storage_address].slide.refresh()
        except AttributeError:
            pass
        return self.opened_slide_storages[storage_address].slide

    async def _set_storage_lock(self, storage_address):
        async with self.lock:
            if storage_address not in self.storage_locks:
                self.storage_locks[storage_address] = asyncio.Lock()

    async def _open_slide(self, storage_address, slide_id):
        slide = await load_slide(storage_address, slide_id)
        self.opened_slide_storages[storage_address] = ExpiringSlide(slide)

    def _reset_slide_expiration(self, storage_address):
        expiring_slide = self.opened_slide_storages[storage_address]
        if expiring_slide.timer is not None:
            expiring_slide.timer.cancel()
        expiring_slide.timer = self.event_loop.call_later(self.timeout, self._close_slide, storage_address)
        logger.debug("Set expiration timer for storage address (%s): %s", storage_address, self.timeout)

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

    def _close_slide(self, storage_address):
        if storage_address in self.opened_slide_storages:
            self.opened_slide_storages[storage_address].slide.close()
            del self.opened_slide_storages[storage_address]
            logger.debug("Closed slide with storage address: %s", storage_address)
