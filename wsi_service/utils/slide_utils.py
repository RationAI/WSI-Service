from collections import OrderedDict

from wsi_service.models.v3.slide import SlideChannel, SlideColor, SlideExtent, SlideLevel
from wsi_service.singletons import logger


class ExpiringSlide:
    def __init__(self, slide, timer=None):
        self.slide = slide
        self.timer = timer


class LRUCache:
    def __init__(self, size):
        self.cache = OrderedDict()
        self.maxSize = size

    def get_all(self):
        return self.cache

    def has_item(self, key):
        return key in self.cache

    def get_item(self, key):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put_item(self, key, item):
        self.cache[key] = item
        self.cache.move_to_end(key)
        if len(self.cache) > self.maxSize:
            removed_item = self.cache.popitem(last=False)
            logger.debug("Removing item from cache: %s", removed_item)
            return removed_item

    def pop_item(self, key):
        return self.cache.pop(key)


def get_tile_width(slide_info, level, tile_x, tile_y):
    level_extent = slide_info.levels[level].extent
    tile_extent = slide_info.tile_extent
    tile_count_x = int(level_extent.x / tile_extent.x)
    tile_count_y = int(level_extent.y / tile_extent.y)
    return (
        tile_extent.x if tile_x < tile_count_x else level_extent.x % tile_extent.x,
        tile_extent.y if tile_y < tile_count_y else level_extent.y %tile_extent.y,
    )


def get_original_levels(level_count, level_dimensions, level_downsamples):
    levels = []
    for level in range(level_count):
        levels.append(
            SlideLevel(
                extent=SlideExtent(x=level_dimensions[level][0], y=level_dimensions[level][1], z=1),
                downsample_factor=level_downsamples[level],
            )
        )
    return levels


def get_rgb_channel_list():
    channels = []
    channels.append(SlideChannel(id=0, name="Red", color=SlideColor(r=255, g=0, b=0, a=0)))
    channels.append(SlideChannel(id=1, name="Green", color=SlideColor(r=0, g=255, b=0, a=0)))
    channels.append(SlideChannel(id=2, name="Blue", color=SlideColor(r=0, g=0, b=255, a=0)))
    return channels
