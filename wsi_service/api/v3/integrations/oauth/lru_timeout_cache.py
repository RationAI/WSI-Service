import asyncio
from collections import OrderedDict


class LRUTimeoutCache:
    def __init__(self, size, timeout):
        self.event_loop = asyncio.get_event_loop()
        self.cache = OrderedDict()
        self.maxSize = size
        self.timeout = timeout

    def get_all(self):
        return self.cache

    def has_item(self, key):
        return key in self.cache

    def get_item(self, key):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        item = self.cache[key]
        self.update_timer(item, key)
        return item

    def put_item(self, key, item):
        if key in self.cache:
            existing_item = self.cache[key]
            existing_item.__timer.cancel()
            del existing_item.__timer

        self.update_timer(item, key)
        self.cache[key] = item
        self.cache.move_to_end(key)

        if len(self.cache) > self.maxSize:
            removed_item = self.cache.popitem(last=False)
            removed_item.__timer.cancel()
            del removed_item.__timer
            return removed_item

    def update_timer(self, item, key):
        if item.__timer is not None:
            item.__timer.cancel()
        item.__timer = self.event_loop.call_later(self.timeout, self._delete_outdated,key)

    def _delete_outdated(self, key):
        del self.cache[key]

    def pop_item(self, key):
        return self.cache.pop(key)