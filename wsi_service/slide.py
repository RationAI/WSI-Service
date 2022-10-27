class Slide(object):
    @classmethod
    async def create(cls, filepath):
        self = cls()
        self.filepath = filepath
        await self.open(filepath)
        return self

    async def open(self, filepath):
        raise NotImplementedError

    async def close(self):
        raise NotImplementedError

    async def get_info(self):
        raise NotImplementedError

    async def get_thumbnail(self, max_x, max_y):
        # allowed to return pil image or numpy array
        raise NotImplementedError

    async def get_label(self):
        # allowed to return pil image or numpy array
        raise NotImplementedError

    async def get_macro(self):
        # allowed to return pil image or numpy array
        raise NotImplementedError

    async def get_region(self, level, start_x, start_y, size_x, size_y, padding_color=None, z=0):
        # allowed to return pil image or numpy array
        raise NotImplementedError

    async def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0):
        # allowed to return pil image or numpy array
        raise NotImplementedError

    # Optional:
    # async def get_tile_raw(self, level, tile_x, tile_y, padding_color=None, z=0):
    #     raise NotImplementedError
    # Note:
    # WSI Service checks if it is available and
    # uses it for tile requests for fully overlapping tiles
