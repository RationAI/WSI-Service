from pydantic import BaseModel, Field
from enum import Enum
from fastapi import Query


# Models

class Extent(BaseModel):
    x: int = Field(..., description="Extent x in horizontal direction")
    y: int = Field(..., description="Extent x in vertical direction")


class SlideInfo(BaseModel):
    extent: Extent = Field(..., description="Image extent (finest level, level=0)")
    num_levels: int = Field(..., description="Number of levels in image pyramid")
    pixel_size_nm: int = Field(..., description="Pixel Size in nm (finest level, level=0)")
    tile_extent: Extent = Field(..., description="Tile extent")


# Queries

ImageFormatsQuery = Query('jpeg', description="Image format (e.g. bmp, gif, jpeg, png, tiff)")


ImageQualityQuery = Query(90, ge=0, le=100, description="Image quality (only considered for specific formats)")


# Responses

ImageResponses = {
    200: {
        "content": {"image/*": {}}
    },
    404: {
        'detail': 'Invalid global_slide_id'
    }
}


ImageRegionResponse = ImageResponses
ImageRegionResponse[413] = {
    'detail': 'Requested region is too large'
}
