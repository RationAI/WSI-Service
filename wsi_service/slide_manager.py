import asyncio
import os

import aiohttp
from fastapi import HTTPException

from wsi_service.plugins import load_slide
from wsi_service.slide_utils import ExpiringSlide, SlideHandleCache

from .singletons import logger


class SlideManager:
    def __init__(self, mapper_address, data_dir, timeout, cache_size=50):
        self.mapper_address = mapper_address
        self.data_dir = data_dir
        self.timeout = timeout
        self.storage_mapper = {}
        self.slide_cache = SlideHandleCache(cache_size)
        self.lock = asyncio.Lock()
        self.storage_locks = {}
        self.event_loop = asyncio.get_event_loop()

    async def get_slide(self, slide_id):
        if slide_id in self.storage_mapper:
            storage_address = self.storage_mapper[slide_id]
        else:
            main_storage_address = await self._get_slide_main_storage_address(slide_id)
            storage_address = os.path.join(self.data_dir, main_storage_address["address"])
            self.storage_mapper[slide_id] = storage_address

        logger.debug("Storage address for slide %s: %s", slide_id, storage_address)

        await self._set_storage_lock(storage_address)

        exp_slide = self.slide_cache.get_slide(storage_address)
        if exp_slide is None:
            async with self.storage_locks[storage_address]:
                slide = await load_slide(storage_address)
                exp_slide = ExpiringSlide(slide)
                self.slide_cache.put_slide(storage_address, exp_slide)
                logger.debug("New slide handle opened for storage address: %s", storage_address)

        self._reset_slide_expiration(storage_address, exp_slide)

        try:  # check if slide is up-to-date (and update) if supported
            await exp_slide.slide.refresh()
        except AttributeError:
            pass

        # overwrite dummy id with current slide id
        exp_slide.slide.slide_info.id = slide_id
        return exp_slide.slide

    def close(self):
        for storage_address, slide in self.slide_cache.get_all().items():
            slide.timer.cancel()
            self._sync_close_slide(storage_address)

    async def _set_storage_lock(self, storage_address):
        async with self.lock:
            if storage_address not in self.storage_locks:
                self.storage_locks[storage_address] = asyncio.Lock()

    def _reset_slide_expiration(self, storage_address, expiring_slide):
        if expiring_slide.timer is not None:
            expiring_slide.timer.cancel()
        expiring_slide.timer = self.event_loop.call_later(self.timeout, self._sync_close_slide, storage_address)
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

    def _sync_close_slide(self, storage_address):
        asyncio.create_task(self._close_slide(storage_address))

    async def _close_slide(self, storage_address):
        if self.slide_cache.has_slide(storage_address):
            exp_slide = self.slide_cache.pop_slide(storage_address)
            await exp_slide.slide.close()
            logger.debug("Closed slide with storage address: %s", storage_address)
