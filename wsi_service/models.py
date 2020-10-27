from typing import List

from pydantic import BaseModel, Field


class Extent(BaseModel):
    x: int = Field(..., description="Extent x in horizontal direction")
    y: int = Field(..., description="Extent x in vertical direction")


class SlideInfo(BaseModel):
    extent: Extent = Field(..., description="Image extent (finest level, level=0)")
    num_levels: int = Field(..., description="Number of levels in image pyramid")
    pixel_size_nm: int = Field(
        ..., description="Pixel Size in nm (finest level, level=0)"
    )
    tile_extent: Extent = Field(..., description="Tile extent")


class StorageAddress(BaseModel):
    address: str
    main_address: bool
    global_storage_address_id: str
    global_slide_id: str


class SlideStorage(BaseModel):
    global_slide_id: str
    storage_type: str
    storage_addresses: List[StorageAddress]
