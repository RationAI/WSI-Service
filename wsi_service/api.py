import os
import pathlib
from typing import List

from fastapi import FastAPI, HTTPException, Path, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from PIL import Image

from wsi_service.api_utils import (
    make_response,
    validate_hex_color_string,
    validate_image_channels,
    validate_image_request,
)
from wsi_service.local_mapper import LocalMapper
from wsi_service.local_mapper_models import CaseLocalMapper, SlideLocalMapper, SlideStorage
from wsi_service.models.slide import SlideInfo
from wsi_service.plugins import get_plugins_overview
from wsi_service.queries import (
    ImageChannelQuery,
    ImageFormatsQuery,
    ImagePaddingColorQuery,
    ImageQualityQuery,
    ZStackQuery,
)
from wsi_service.responses import ImageRegionResponse, ImageResponses
from wsi_service.service_status import WSIServiceStatus
from wsi_service.singletons import settings
from wsi_service.slide_manager import SlideManager

api = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json" if not settings.disable_openapi else "",
    root_path=settings.root_path,
)

if settings.cors_allow_origins:
    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

slide_manager = SlideManager(
    settings.mapper_address,
    settings.data_dir,
    settings.inactive_histo_image_timeout_seconds,
    settings.image_handle_cache_size,
)


@api.get("/alive", response_model=WSIServiceStatus, status_code=status.HTTP_200_OK)
async def get_service_status():
    return WSIServiceStatus(
        status="ok", version=settings.version, plugins=get_plugins_overview(), plugins_default=settings.plugins_default
    )


@api.get("/v1/slides/{slide_id}/info", response_model=SlideInfo, tags=["Main Routes"])
async def get_slide_info(slide_id: str):
    """
    Get metadata information for a slide given its ID
    """
    return await slide_manager.get_slide_info(slide_id)


@api.get(
    "/v1/slides/{slide_id}/thumbnail/max_size/{max_x}/{max_y}",
    responses=ImageResponses,
    response_class=StreamingResponse,
    tags=["Main Routes"],
)
async def get_slide_thumbnail(
    slide_id: str,
    max_x: int = Path(
        None, example=100, ge=1, le=settings.max_thumbnail_size, description="Maximum width of thumbnail"
    ),
    max_y: int = Path(
        None, example=100, ge=1, le=settings.max_thumbnail_size, description="Maximum height of thumbnail"
    ),
    image_format: str = ImageFormatsQuery,
    image_quality: int = ImageQualityQuery,
):
    """
    Get slide thumbnail image  given its ID.
    You additionally need to set a maximum width and height for the thumbnail.
    Images will be scaled to match these requirements while keeping the aspect ratio.

    Optionally, the image format and its quality (e.g. for jpeg) can be selected.
    Formats include jpeg, png, tiff, bmp, gif.
    When tiff is specified as output format the raw data of the image is returned.
    """
    validate_image_request(image_format, image_quality)
    slide = await slide_manager.get_slide(slide_id)
    thumbnail = await slide.get_thumbnail(max_x, max_y)
    return make_response(slide, thumbnail, image_format, image_quality)


@api.get(
    "/v1/slides/{slide_id}/label/max_size/{max_x}/{max_y}",
    responses=ImageResponses,
    response_class=StreamingResponse,
    tags=["Main Routes"],
)
async def get_slide_label(
    slide_id: str,
    max_x: int = Path(None, example=100, description="Maximum width of label image"),
    max_y: int = Path(None, example=100, description="Maximum height of label image"),
    image_format: str = ImageFormatsQuery,
    image_quality: int = ImageQualityQuery,
):
    """
    Get the label image of a slide given its ID.
    You additionally need to set a maximum width and height for the label image.
    Images will be scaled to match these requirements while keeping the aspect ratio.

    Optionally, the image format and its quality (e.g. for jpeg) can be selected.
    Formats include jpeg, png, tiff, bmp, gif.
    When tiff is specified as output format the raw data of the image is returned.
    """
    validate_image_request(image_format, image_quality)
    slide = await slide_manager.get_slide(slide_id)
    label = await slide.get_label()
    label.thumbnail((max_x, max_y), Image.ANTIALIAS)
    return make_response(slide, label, image_format, image_quality)


@api.get(
    "/v1/slides/{slide_id}/macro/max_size/{max_x}/{max_y}",
    responses=ImageResponses,
    response_class=StreamingResponse,
    tags=["Main Routes"],
)
async def get_slide_macro(
    slide_id: str,
    max_x: int = Path(None, example=100, description="Maximum width of macro image"),
    max_y: int = Path(None, example=100, description="Maximum height of macro image"),
    image_format: str = ImageFormatsQuery,
    image_quality: int = ImageQualityQuery,
):
    """
    Get the macro image of a slide given its ID.
    You additionally need to set a maximum width and height for the macro image.
    Images will be scaled to match these requirements while keeping the aspect ratio.

    Optionally, the image format and its quality (e.g. for jpeg) can be selected.
    Formats include jpeg, png, tiff, bmp, gif.
    When tiff is specified as output format the raw data of the image is returned.
    """
    validate_image_request(image_format, image_quality)
    slide = await slide_manager.get_slide(slide_id)
    macro = await slide.get_macro()
    macro.thumbnail((max_x, max_y), Image.ANTIALIAS)
    return make_response(slide, macro, image_format, image_quality)


@api.get(
    "/v1/slides/{slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}",
    responses=ImageRegionResponse,
    response_class=StreamingResponse,
    tags=["Main Routes"],
)
async def get_slide_region(
    slide_id: str,
    level: int = Path(None, ge=0, example=0, description="Pyramid level of region"),
    start_x: int = Path(None, example=0, description="x component of start coordinate of requested region"),
    start_y: int = Path(None, example=0, description="y component of start coordinate of requested region"),
    size_x: int = Path(None, example=1024, description="Width of requested region"),
    size_y: int = Path(None, example=1024, description="Height of requested region"),
    image_channels: List[int] = ImageChannelQuery,
    z: int = ZStackQuery,
    image_format: str = ImageFormatsQuery,
    image_quality: int = ImageQualityQuery,
):
    """
    Get a region of a slide given its ID and by providing the following parameters:

    * `level` - Pyramid level of the region. Level 0 is highest (original) resolution. The available levels depend on the image.

    * `start_x`, `start_y` - Start coordinates of the requested region. Coordinates are given with respect to the requested level. Coordinates define the upper left corner of the region with respect to the image origin (0, 0) at the upper left corner of the image.

    * `size_x`, `size_y` - Width and height of requested region. Size needs to be given with respect to the requested level.

    There are a number of addtional query parameters:

    * `image_channels` - Single channels (or multiple channels) can be retrieved through the optional parameter image_channels as an integer array referencing the channel IDs. This is paricularly important for images with abitrary image channels and channels with a higher color depth than 8bit (e.g. fluorescence images). The channel composition of the image can be obtained through the slide info endpoint, where the dedicated channels are listed along with its color, name and bitness. By default all channels are returned.

    * `z` - The region endpoint also offers the selection of a layer in a Z-Stack by setting the index z. Default is z=0.

    * `image_format` - The image format can be selected. Formats include jpeg, png, tiff, bmp, gif. When tiff is specified as output format the raw data of the image is returned. Multi-channel images can also be represented as RGB-images (mostly for displaying reasons in the viewer). Note that the mapping of all color channels to RGB values is currently restricted to the first three channels. Default is jpeg.

    * `image_quality` - The image quality can be set for specific formats, e.g. for the jpeg format a value between 0 and 100 can be selected. Default is 90.
    """
    validate_image_request(image_format, image_quality)
    if size_x * size_y > settings.max_returned_region_size:
        raise HTTPException(
            status_code=403,
            detail=f"Requested region may not contain more than {settings.max_returned_region_size} pixels.",
        )
    if size_x * size_y == 0:
        raise HTTPException(status_code=422, detail="Requested region must contain at least 1 pixel.")

    slide = await slide_manager.get_slide(slide_id)
    if z != 0:
        try:
            image_region = await slide.get_region(level, start_x, start_y, size_x, size_y, padding_color=None, z=z)
        except TypeError as e:
            raise HTTPException(
                status_code=422, detail=f"""Invalid ZStackQuery z={z}. The image does not support multiple z-layers."""
            ) from e
    else:
        image_region = await slide.get_region(level, start_x, start_y, size_x, size_y, padding_color=None)
    validate_image_channels(slide, image_channels)
    return make_response(slide, image_region, image_format, image_quality, image_channels)


@api.get(
    "/v1/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}",
    responses=ImageResponses,
    response_class=StreamingResponse,
    tags=["Main Routes"],
)
async def get_slide_tile(
    slide_id: str,
    level: int = Path(None, ge=0, example=0, description="Pyramid level of region"),
    tile_x: int = Path(None, example=0, description="Request the tile_x-th tile in x dimension"),
    tile_y: int = Path(None, example=0, description="Request the tile_y-th tile in y dimension"),
    image_channels: List[int] = ImageChannelQuery,
    z: int = ZStackQuery,
    padding_color: str = ImagePaddingColorQuery,
    image_format: str = ImageFormatsQuery,
    image_quality: int = ImageQualityQuery,
):
    """
    Get a tile of a slide given its ID and by providing the following parameters:

    * `level` - Pyramid level of the tile. Level 0 is highest (original) resolution. The available levels depend on the image.

    * `tile_x`, `tile_y` - Coordinates are given with respect to tiles, i.e. tile coordinate n is the n-th tile in the respective dimension. Coordinates are also given with respect to the requested level. Coordinates (0,0) select the tile at the upper left corner of the image.

    There are a number of addtional query parameters:

    * `image_channels` - Single channels (or multiple channels) can be retrieved through the optional parameter image_channels as an integer array referencing the channel IDs. This is paricularly important for images with abitrary image channels and channels with a higher color depth than 8bit (e.g. fluorescence images). The channel composition of the image can be obtained through the slide info endpoint, where the dedicated channels are listed along with its color, name and bitness. By default all channels are returned.

    * `z` - The region endpoint also offers the selection of a layer in a Z-Stack by setting the index z. Default is z=0.

    * `padding_color` - Background color as 24bit-hex-string with leading #, that is used when image tile contains whitespace when out of image extent. Default is white.

    * `image_format` - The image format can be selected. Formats include jpeg, png, tiff, bmp, gif. When tiff is specified as output format the raw data of the image is returned. Multi-channel images can also be represented as RGB-images (mostly for displaying reasons in the viewer). Note that the mapping of all color channels to RGB values is currently restricted to the first three channels. Default is jpeg.

    * `image_quality` - The image quality can be set for specific formats, e.g. for the jpeg format a value between 0 and 100 can be selected. Default is 90.
    """
    vp_color = validate_hex_color_string(padding_color)
    validate_image_request(image_format, image_quality)
    slide = await slide_manager.get_slide(slide_id)
    if z != 0:
        try:
            image_tile = await slide.get_tile(level, tile_x, tile_y, padding_color=vp_color, z=z)
        except TypeError as e:
            raise HTTPException(
                status_code=422, detail=f"""Invalid ZStackQuery z={z}. The image does not support multiple z-layers."""
            ) from e
    else:
        image_tile = await slide.get_tile(level, tile_x, tile_y, padding_color=vp_color)
    validate_image_channels(slide, image_channels)
    return make_response(slide, image_tile, image_format, image_quality, image_channels)


@api.on_event("shutdown")
async def shutdown_event():
    await slide_manager.close()


if settings.local_mode:
    localmapper = LocalMapper(settings.data_dir)

    @api.get("/v1/cases/", response_model=List[CaseLocalMapper], tags=["Additional Routes (Standalone WSI Service)"])
    async def get_cases():
        """
        (Only in standalone mode) Browse the local directory and return case ids for each available directory.
        """
        cases = localmapper.get_cases()
        return cases

    @api.get(
        "/v1/cases/{case_id}/slides/",
        response_model=List[SlideLocalMapper],
        tags=["Additional Routes (Standalone WSI Service)"],
    )
    async def get_available_slides(case_id: str):
        """
        (Only in standalone mode) Browse the local case directory and return slide ids for each available file.
        """
        slides = localmapper.get_slides(case_id)
        return slides

    @api.get(
        "/v1/slides/{slide_id}", response_model=SlideLocalMapper, tags=["Additional Routes (Standalone WSI Service)"]
    )
    async def get_slide(slide_id: str):
        """
        (Only in standalone mode) Return slide data for a given slide ID.
        """
        slide = localmapper.get_slide(slide_id)
        return slide

    @api.get(
        "/v1/slides/{slide_id}/storage",
        response_model=SlideStorage,
        tags=["Additional Routes (Standalone WSI Service)"],
    )
    async def get_slide_storage(slide_id: str):
        """
        (Only in standalone mode) Return slide storage data for a given slide ID.
        """
        slide = localmapper.get_slide(slide_id)
        return slide.slide_storage

    @api.get("/v1/refresh_local_mapper", tags=["Additional Routes (Standalone WSI Service)"])
    async def refresh_local_mapper():
        """
        (Only in standalone mode) Refresh available files by scanning for new files.
        """
        localmapper.refresh()
        return JSONResponse({"detail": "Local mapper has been refreshed."}, status_code=200)


if settings.enable_viewer_routes:

    @api.get("/v1/slides/{slide_id}/viewer", response_class=HTMLResponse, include_in_schema=False)
    async def viewer(slide_id: str):
        viewer_html = open(
            os.path.join(pathlib.Path(__file__).parent.absolute(), "viewer.html"), "r", encoding="utf-8"
        ).read()
        viewer_html = viewer_html.replace("REPLACE_SLIDE_ID", slide_id)
        return viewer_html


if settings.enable_viewer_routes and settings.local_mode:

    @api.get("/v1/validation_viewer", response_class=HTMLResponse, include_in_schema=False)
    async def validation_viewer():
        validation_viewer_html = open(
            os.path.join(pathlib.Path(__file__).parent.absolute(), "validation_viewer.html"), "r", encoding="utf-8"
        ).read()
        return validation_viewer_html
