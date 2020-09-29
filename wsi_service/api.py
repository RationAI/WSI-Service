from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder

from wsi_service.settings import Settings
from wsi_service.local_mapper import LocalMapper
from wsi_service.slide_source import SlideSource
from wsi_service.api_utils import validate_image_request, make_image_response
from wsi_service.models import SlideInfo


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


@api.get('/slides/{global_slide_id}/thumbnail/max_size/{max_x}/{max_y}')
def get_slide_thumbnail(global_slide_id: str, max_x: int, max_y: int, image_format: str = "jpeg", image_quality: int = 90):
    """
    Thumbnail of slide with given maximum size
    """
    validate_image_request(image_format, image_quality)
    slide = slide_source.get_slide(global_slide_id)
    thumbnail = slide.get_thumbnail(max_x, max_y)
    return make_image_response(thumbnail, image_format, image_quality)


@api.get('/slides/{global_slide_id}/label')
def get_slide_label(global_slide_id: str, image_format: str = "jpeg", image_quality: int = 90):
    """
    The label image of the slide
    """
    validate_image_request(image_format, image_quality)
    slide = slide_source.get_slide(global_slide_id)
    label = slide.get_label()
    return make_image_response(label, image_format, image_quality)


@api.get('/slides/{global_slide_id}/macro')
def get_slide_macro(global_slide_id: str, image_format: str = "jpeg", image_quality: int = 90):
    """
    The macro image of the slide
    """
    validate_image_request(image_format, image_quality)
    slide = slide_source.get_slide(global_slide_id)
    macro = slide.get_macro()
    return make_image_response(macro, image_format, image_quality)


@api.get(
    '/slides/{global_slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}',
    responses={
        200: {
            "content": {"image/*": {}}
        }
    }
)
def get_slide_region(global_slide_id: str, level: int, start_x: int, start_y: int, size_x: int, size_y: int, image_format: str = "jpeg", image_quality: int = 90):
    """
    Get region of the slide. Level 0 is highest (original) resolution. Each level has half the
    resolution and half the extent of the previous level. Coordinates are given with respect
    to the requested level.
    """
    validate_image_request(image_format, image_quality)
    if size_x * size_y > settings.max_returned_region_size:
        raise HTTPException(status_code=413, detail=f'Requested region may not contain more than {settings.max_returned_region_size} pixels')
    slide = slide_source.get_slide(global_slide_id)
    img = slide.get_region(level, start_x, start_y, size_x, size_y)
    return make_image_response(img, image_format, image_quality)


@api.get('/slides/{global_slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}')
def get_slide_tile(global_slide_id: str, level: int, tile_x: int, tile_y: int, image_format: str = "jpeg", image_quality: int = 90):
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

    @api.get('/cases/{global_case_id}/slides/')
    def get_available_slides(global_case_id: str):
        """
        (Only in local mode) Browse the local directory and return slide ids for each available file.
        """
        localmapper = LocalMapper(settings.data_dir)
        slides = localmapper.get_slides(global_case_id)
        return slides

    @api.get('/slides/{global_slide_id}')
    def get_slide(global_slide_id: str):
        """
        (Only in local mode) Return slide storage data for a given global_slide_id.
        """
        localmapper = LocalMapper(settings.data_dir)
        slide = localmapper.get_slide(global_slide_id)
        return slide
