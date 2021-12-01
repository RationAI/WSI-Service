from collections import OrderedDict

from wsi_service.models.slide import SlideChannel, SlideColor, SlideExtent, SlideLevel

from .singletons import logger


class ExpiringSlide:
    def __init__(self, slide, timer=None):
        self.slide = slide
        self.timer = timer


class SlideHandleCache:
    def __init__(self, size):
        self.cache = OrderedDict()
        self.maxSize = size

    def get_all(self):
        return self.cache

    def has_slide(self, key):
        return key in self.cache

    def get_slide(self, key):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put_slide(self, key, slide):
        self.cache[key] = slide
        self.cache.move_to_end(key)
        if len(self.cache) > self.maxSize:
            removed_slide_handle = self.cache.popitem(last=False)
            logger.debug("Removing slide handle from cache: %s", removed_slide_handle)
            return removed_slide_handle

    def pop_slide(self, key):
        return self.cache.popitem(key)[1]


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
