import os
import pathlib
from typing import List

from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

from wsi_service.api_utils import make_image_response, validate_image_request
from wsi_service.local_mapper import LocalMapper
from wsi_service.local_mapper_models import (
    CaseLocalMapper,
    SlideLocalMapper,
    SlideStorage,
)
from wsi_service.models.slide import SlideInfo
from wsi_service.queries import ImageFormatsQuery, ImageQualityQuery, ZStackQuery
from wsi_service.responses import ImageRegionResponse, ImageResponses
from wsi_service.settings import Settings
from wsi_service.slide_source import SlideSource

settings = Settings()

api = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
    docs_url="/",
    redoc_url=None,
    openapi_url="/openapi.json" if not settings.disable_openapi else "",
    root_path=settings.root_path,
)

if settings.cors_allow_origins:
    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

slide_source = SlideSource(
    settings.mapper_address,
    settings.data_dir,
    settings.inactive_histo_image_timeout_seconds,
)


@api.get("/v1/slides/{slide_id}/info", response_model=SlideInfo, tags=["Main Routes"])
def get_slide_info(slide_id: str):
    """
    Metadata for slide with given id
    """
    slide = slide_source.get_slide(slide_id)
    return slide.get_info()


@api.get(
    "/v1/slides/{slide_id}/thumbnail/max_size/{max_x}/{max_y}",
    responses=ImageResponses,
    response_class=StreamingResponse,
    tags=["Main Routes"],
)
def get_slide_thumbnail(
    slide_id: str,
    max_x: int = Path(None, example=100, description="Maximum width of thumbnail"),
    max_y: int = Path(None, example=100, description="Maximum height of thumbnail"),
    image_format: str = ImageFormatsQuery,
    image_quality: int = ImageQualityQuery,
):
    """
    Thumbnail of the slide
    """
    validate_image_request(image_format, image_quality)
    slide = slide_source.get_slide(slide_id)
    thumbnail = slide.get_thumbnail(max_x, max_y)
    return make_image_response(thumbnail, image_format, image_quality)


@api.get(
    "/v1/slides/{slide_id}/label",
    responses=ImageResponses,
    response_class=StreamingResponse,
    tags=["Main Routes"],
)
def get_slide_label(
    slide_id: str,
    image_format: str = ImageFormatsQuery,
    image_quality: int = ImageQualityQuery,
):
    """
    Label image of the slide
    """
    validate_image_request(image_format, image_quality)
    slide = slide_source.get_slide(slide_id)
    label = slide.get_label()
    return make_image_response(label, image_format, image_quality)


@api.get(
    "/v1/slides/{slide_id}/macro",
    responses=ImageResponses,
    response_class=StreamingResponse,
    tags=["Main Routes"],
)
def get_slide_macro(
    slide_id: str,
    image_format: str = ImageFormatsQuery,
    image_quality: int = ImageQualityQuery,
):
    """
    Macro image of the slide
    """
    validate_image_request(image_format, image_quality)
    slide = slide_source.get_slide(slide_id)
    macro = slide.get_macro()
    return make_image_response(macro, image_format, image_quality)


@api.get(
    "/v1/slides/{slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}",
    responses=ImageRegionResponse,
    response_class=StreamingResponse,
    tags=["Main Routes"],
)
def get_slide_region(
    slide_id: str,
    level: int = Path(None, ge=0, example=0, description="Pyramid level of region"),
    start_x: int = Path(
        None,
        example=0,
        description="x component of start coordinate of requested region",
    ),
    start_y: int = Path(
        None,
        example=0,
        description="y component of start coordinate of requested region",
    ),
    size_x: int = Path(None, example=1024, description="Width of requested region"),
    size_y: int = Path(None, example=1024, description="Height of requested region"),
    image_format: str = ImageFormatsQuery,
    image_quality: int = ImageQualityQuery,
    z: int = ZStackQuery,
):
    """
    Get region of the slide. Level 0 is highest (original) resolution. Each level has half the
    resolution and half the extent of the previous level. Coordinates are given with respect
    to the requested level.
    """
    validate_image_request(image_format, image_quality)
    if size_x * size_y > settings.max_returned_region_size:
        raise HTTPException(
            status_code=403,
            detail=f"Requested region may not contain more than {settings.max_returned_region_size} pixels.",
        )
    if size_x * size_y == 0:
        raise HTTPException(
            status_code=422,
            detail=f"Requested region must contain at least 1 pixel.",
        )
    slide = slide_source.get_slide(slide_id)
    img = slide.get_region(level, start_x, start_y, size_x, size_y)
    return make_image_response(img, image_format, image_quality)


@api.get(
    "/v1/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}",
    responses=ImageResponses,
    response_class=StreamingResponse,
    tags=["Main Routes"],
)
def get_slide_tile(
    slide_id: str,
    level: int = Path(None, ge=0, example=0, description="Pyramid level of region"),
    tile_x: int = Path(None, example=0, description="Request the tile_x-th tile in x dimension"),
    tile_y: int = Path(None, example=0, description="Request the tile_y-th tile in y dimension"),
    image_format: str = ImageFormatsQuery,
    image_quality: int = ImageQualityQuery,
    z: int = ZStackQuery,
):
    """
    Get tile of the slide. Extent of the tile is given in slide metadata. Level 0 is highest
    (original) resolution. Each level has half the resolution and half the extent of the
    previous level. Coordinates are given with respect to tiles, i.e. tile coordinate n is the
    n-th tile in the respective dimension.
    """
    validate_image_request(image_format, image_quality)
    slide = slide_source.get_slide(slide_id)
    img = slide.get_tile(level, tile_x, tile_y)
    return make_image_response(img, image_format, image_quality)


if settings.local_mode:

    @api.get(
        "/v1/cases/",
        response_model=List[CaseLocalMapper],
        tags=["Additional Routes (Standalone WSI Service)"],
    )
    def get_cases():
        """
        (Only in standalone mode) Browse the local directory and return case ids for each available directory.
        """
        localmapper = LocalMapper(settings.data_dir)
        cases = localmapper.get_cases()
        return cases

    @api.get(
        "/v1/cases/{case_id}/slides/",
        response_model=List[SlideLocalMapper],
        tags=["Additional Routes (Standalone WSI Service)"],
    )
    def get_available_slides(case_id: str):
        """
        (Only in standalone mode) Browse the local case directory and return slide ids for each available file.
        """
        localmapper = LocalMapper(settings.data_dir)
        slides = localmapper.get_slides(case_id)
        return slides

    @api.get(
        "/v1/slides/{slide_id}",
        response_model=SlideLocalMapper,
        tags=["Additional Routes (Standalone WSI Service)"],
    )
    def get_slide(slide_id: str):
        """
        (Only in standalone mode) Return slide data for a given slide_id.
        """
        localmapper = LocalMapper(settings.data_dir)
        slide = localmapper.get_slide(slide_id)
        return slide

    @api.get(
        "/v1/slides/{slide_id}/storage",
        response_model=SlideStorage,
        tags=["Additional Routes (Standalone WSI Service)"],
    )
    def get_slide_storage(slide_id: str):
        """
        (Only in standalone mode) Return slide storage data for a given slide_id.
        """
        localmapper = LocalMapper(settings.data_dir)
        slide = localmapper.get_slide(slide_id)
        return slide.slide_storage

    @api.get(
        "/v1/slides/{slide_id}/viewer",
        response_class=HTMLResponse,
        include_in_schema=False,
        tags=["Additional Routes (Standalone WSI Service)"],
    )
    def view_slide(slide_id: str):
        viewer_html = open(
            os.path.join(pathlib.Path(__file__).parent.absolute(), "viewer.html"),
            "r",
            encoding="utf-8",
        ).read()
        viewer_html = viewer_html.replace("REPLACE_SLIDE_ID", slide_id)
        return viewer_html
