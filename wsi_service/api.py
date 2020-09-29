from typing import List

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from wsi_service.settings import Settings
from wsi_service.local_mapper import LocalMapper
from wsi_service.slide_source import SlideSource
from wsi_service.api_utils import validate_image_request, make_image_response
from wsi_service.models import SlideInfo, SlideMapperInfo
from wsi_service.queries import ImageQualityQuery, ImageFormatsQuery
from wsi_service.responses import ImageResponses, ImageRegionResponse


settings = Settings()

api = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
    docs_url="/",
    redoc_url=None
)

slide_source = SlideSource(
    settings.mapper_address,
    settings.data_dir,
    settings.max_returned_region_size
)


@api.get('/slides/{global_slide_id}/info', response_model=SlideInfo)
def get_slide_info(global_slide_id: str):
    """
    Metadata for slide with given id
    """
    slide = slide_source.get_slide(global_slide_id)
    return slide.get_info()


@api.get('/slides/{global_slide_id}/thumbnail/max_size/{max_x}/{max_y}',
         responses=ImageResponses, response_class=StreamingResponse)
def get_slide_thumbnail(
        global_slide_id: str,
        max_x: int = Path(
            None,
            example=100,
            description="Maximum width of thumbnail"),
        max_y: int = Path(
            None,
            example=100,
            description="Maximum height of thumbnail"),
        image_format: str = ImageFormatsQuery,
        image_quality: int = ImageQualityQuery):
    """
    Thumbnail of the slide
    """
    validate_image_request(image_format, image_quality)
    slide = slide_source.get_slide(global_slide_id)
    thumbnail = slide.get_thumbnail(max_x, max_y)
    return make_image_response(thumbnail, image_format, image_quality)


@api.get('/slides/{global_slide_id}/label',
         responses=ImageResponses, response_class=StreamingResponse)
def get_slide_label(
        global_slide_id: str,
        image_format: str = ImageFormatsQuery,
        image_quality: int = ImageQualityQuery):
    """
    Label image of the slide
    """
    validate_image_request(image_format, image_quality)
    slide = slide_source.get_slide(global_slide_id)
    label = slide.get_label()
    return make_image_response(label, image_format, image_quality)


@api.get('/slides/{global_slide_id}/macro',
         responses=ImageResponses, response_class=StreamingResponse)
def get_slide_macro(
        global_slide_id: str,
        image_format: str = ImageFormatsQuery,
        image_quality: int = ImageQualityQuery):
    """
    Macro image of the slide
    """
    validate_image_request(image_format, image_quality)
    slide = slide_source.get_slide(global_slide_id)
    macro = slide.get_macro()
    return make_image_response(macro, image_format, image_quality)


@api.get('/slides/{global_slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}',
         responses=ImageRegionResponse, response_class=StreamingResponse)
def get_slide_region(
        global_slide_id: str,
        level: int = Path(
            None,
            ge=0,
            example=0,
            description="Pyramid level of region"),
        start_x: int = Path(
            None,
            example=0,
            description="x component of start coordinate of requested region"),
        start_y: int = Path(
            None,
            example=0,
            description="y component of start coordinate of requested region"),
        size_x: int = Path(
            None,
            example=1024,
            description="Width of requested region"),
        size_y: int = Path(
            None,
            example=1024,
            description="Height of requested region"),
        image_format: str = ImageFormatsQuery,
        image_quality: int = ImageQualityQuery):
    """
    Get region of the slide. Level 0 is highest (original) resolution. Each level has half the
    resolution and half the extent of the previous level. Coordinates are given with respect
    to the requested level.
    """
    validate_image_request(image_format, image_quality)
    if size_x * size_y > settings.max_returned_region_size:
        raise HTTPException(
            status_code=413,
            detail=f'Requested region may not contain more than {settings.max_returned_region_size} pixels')
    slide = slide_source.get_slide(global_slide_id)
    img = slide.get_region(level, start_x, start_y, size_x, size_y)
    return make_image_response(img, image_format, image_quality)


@api.get('/slides/{global_slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}',
         responses=ImageResponses, response_class=StreamingResponse)
def get_slide_tile(
        global_slide_id: str,
        level: int = Path(
            None,
            ge=0,
            example=0,
            description="Pyramid level of region"),
        tile_x: int = Path(
            None,
            example=0,
            description="Request the tile_x-th tile in x dimension"),
        tile_y: int = Path(
            None,
            example=0,
            description="Request the tile_y-th tile in y dimension"),
        image_format: str = ImageFormatsQuery,
        image_quality: int = ImageQualityQuery):
    """
    Get tile of the slide. Extent of the tile is given in slide metadata. Level 0 is highest
    (original) resolution. Each level has half the resolution and half the extent of the
    previous level. Coordinates are given with respect to tiles, i.e. tile coordinate n is the
    n-th tile in the respective dimension.
    """
    validate_image_request(image_format, image_quality)
    slide = slide_source.get_slide(global_slide_id)
    img = slide.get_tile(level, tile_x, tile_y)
    return make_image_response(img, image_format, image_quality)


if settings.local_mode:

    @api.get('/cases/')
    def get_cases():
        """
        (Only in local mode) Browse the local directory and return case ids for each available directory.
        """
        localmapper = LocalMapper(settings.data_dir)
        cases = localmapper.get_cases()
        return cases

    @api.get('/cases/{global_case_id}/slides/',
             response_model=List[SlideMapperInfo])
    def get_available_slides(global_case_id: str):
        """
        (Only in local mode) Browse the local directory and return slide ids for each available file.
        """
        localmapper = LocalMapper(settings.data_dir)
        slides = localmapper.get_slides(global_case_id)
        return slides

    @api.get('/slides/{global_slide_id}', response_model=SlideMapperInfo)
    def get_slide(global_slide_id: str):
        """
        (Only in local mode) Return slide storage data for a given global_slide_id.
        """
        localmapper = LocalMapper(settings.data_dir)
        slide = localmapper.get_slide(global_slide_id)
        return slide
