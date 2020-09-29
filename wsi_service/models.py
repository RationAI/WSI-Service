from pydantic import BaseModel


class Extent(BaseModel):
    x: int
    y: int


class SlideInfo(BaseModel):
    extent: Extent
    num_levels: int
    pixel_size_nm: int
    tile_extent: Extent
