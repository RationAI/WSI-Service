from typing import List

from fastapi import Path
from fastapi.responses import StreamingResponse
from PIL import Image
from zipfly import ZipFly
from wsi_service.singletons import logger

from wsi_service.custom_models.queries import (
    ImageChannelQuery,
    ImageFormatsQuery,
    ImagePaddingColorQuery,
    ImageQualityQuery,
    PluginQuery,
    ZStackQuery, IdQuery, ICCProfileIntent,
)
from wsi_service.custom_models.responses import ImageRegionResponse, ImageResponses
from wsi_service.models.v3.slide import SlideInfo
from wsi_service.utils.app_utils import (
    make_response,
    validate_hex_color_string,
    validate_image_channels,
    validate_image_level,
    validate_image_request,
    validate_image_size,
    validate_image_z,
)
from wsi_service.custom_models.batch_queries import (
    IdListQuery,
    TileLevelListQuery,
    TileXListQuery,
    TileYListQuery, IdListQuery2,
)
from wsi_service.utils.download_utils import expand_folders, get_zipfly_paths, remove_folders
from wsi_service.utils.image_utils import (
    check_complete_region_overlap,
    check_complete_tile_overlap,
    get_extended_region,
    get_extended_tile,
)
from .singletons import api_integration
from .slides_batch_api_helpers import thumbnail, info, tile, macro, label, batch, icc_profile


def add_routes_slides(app, settings, slide_manager):
    @app.get("/slides/info", response_model=SlideInfo, tags=["Main Routes"])
    async def _(slide_id=IdQuery, plugin: str = PluginQuery, payload=api_integration.global_depends()):
        """
        Get metadata information for a slide given its ID
        """
        slide = await slide_manager.get_slide_info(slide_id, slide_info_model=SlideInfo, plugin=plugin)
        await api_integration.allow_access_slide(auth_payload=payload, slide_id=slide_id, manager=slide_manager,
                                                 plugin=plugin, slide=slide)
        return slide

    @app.get(
        "/slides/thumbnail/max_size/{max_x}/{max_y}",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            slide_id=IdQuery,
            max_x: int = Path(
                examples=[100], ge=1, le=settings.max_thumbnail_size, description="Maximum width of thumbnail"
            ),
            max_y: int = Path(
                examples=[100], ge=1, le=settings.max_thumbnail_size, description="Maximum height of thumbnail"
            ),
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            apply_icc_intent: str = ICCProfileIntent,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
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
        await api_integration.allow_access_slide(auth_payload=payload, slide_id=slide_id, manager=slide_manager,
                                                 plugin=plugin)
        slide = await slide_manager.get_slide(slide_id, plugin=plugin)
        thumbnail = await slide.get_thumbnail(max_x, max_y, apply_icc_intent)
        return make_response(slide, thumbnail, image_format, image_quality)

    @app.get(
        "/slides/label/max_size/{max_x}/{max_y}",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            slide_id=IdQuery,
            max_x: int = Path(examples=[100], description="Maximum width of label image"),
            max_y: int = Path(examples=[100], description="Maximum height of label image"),
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
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
        await api_integration.allow_access_slide(auth_payload=payload, slide_id=slide_id, manager=slide_manager,
                                                 plugin=plugin)
        slide = await slide_manager.get_slide(slide_id, plugin=plugin)
        label = await slide.get_label()
        label.thumbnail((max_x, max_y), Image.Resampling.LANCZOS)
        return make_response(slide, label, image_format, image_quality)

    @app.get(
        "/slides/macro/max_size/{max_x}/{max_y}",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            slide_id=IdQuery,
            max_x: int = Path(examples=[100], description="Maximum width of macro image"),
            max_y: int = Path(examples=[100], description="Maximum height of macro image"),
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            apply_icc_intent: str = ICCProfileIntent,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
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
        await api_integration.allow_access_slide(auth_payload=payload, slide_id=slide_id, manager=slide_manager,
                                                 plugin=plugin)
        slide = await slide_manager.get_slide(slide_id, plugin=plugin)
        macro = await slide.get_macro(apply_icc_intent)
        macro.thumbnail((max_x, max_y), Image.Resampling.LANCZOS)
        return make_response(slide, macro, image_format, image_quality)

    @app.get(
        "/slides/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}",
        responses=ImageRegionResponse,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            slide_id=IdQuery,
            level: int = Path(ge=0, examples=[0], description="Pyramid level of region"),
            start_x: int = Path(examples=[0], description="x component of start coordinate of requested region"),
            start_y: int = Path(examples=[0], description="y component of start coordinate of requested region"),
            size_x: int = Path(gt=0, examples=[1024], description="Width of requested region"),
            size_y: int = Path(gt=0, examples=[1024], description="Height of requested region"),
            image_channels: List[int] = ImageChannelQuery,
            z: int = ZStackQuery,
            padding_color: str = ImagePaddingColorQuery,
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            apply_icc_intent: str = ICCProfileIntent,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
    ):
        """
        Get a region of a slide given its ID and by providing the following parameters:

        * `level` - Pyramid level of the region. Level 0 is highest (original) resolution.
        The available levels depend on the image.

        * `start_x`, `start_y` - Start coordinates of the requested region.
        Coordinates are given with respect to the requested level.
        Coordinates define the upper left corner of the region with respect to the image origin
        (0, 0) at the upper left corner of the image.

        * `size_x`, `size_y` - Width and height of requested region.
        Size needs to be given with respect to the requested level.

        There are a number of addtional query parameters:

        * `image_channels` - Single channels (or multiple channels) can be retrieved through the optional parameter
        image_channels as an integer array referencing the channel IDs.
        This is paricularly important for images with abitrary image channels and channels with a higher
        color depth than 8bit (e.g. fluorescence images).
        The channel composition of the image can be obtained through the slide info endpoint,
        where the dedicated channels are listed along with its color, name and bitness.
        By default all channels are returned.

        * `z` - The region endpoint also offers the selection of a layer in a Z-Stack by setting the index z.
        Default is z=0.

        * `padding_color` - Background color as 24bit-hex-string with leading #,
        that is used when image region contains whitespace when out of image extent. Default is white.
        Only works for 8-bit RGB slides, otherwise the background color is black.

        * `image_format` - The image format can be selected. Formats include jpeg, png, tiff, bmp, gif.
        When tiff is specified as output format the raw data of the image is returned.
        Multi-channel images can also be represented as RGB-images (mostly for displaying reasons in the viewer).
        Note that the mapping of all color channels to RGB values is currently restricted to the first three channels.
        Default is jpeg.

        * `image_quality` - The image quality can be set for specific formats,
        e.g. for the jpeg format a value between 0 and 100 can be selected. Default is 90.
        """
        vp_color = validate_hex_color_string(padding_color)
        validate_image_request(image_format, image_quality)
        validate_image_size(size_x, size_y)
        await api_integration.allow_access_slide(auth_payload=payload, slide_id=slide_id, manager=slide_manager,
                                                 plugin=plugin)
        slide = await slide_manager.get_slide(slide_id, plugin=plugin)
        slide_info = await slide.get_info()
        validate_image_level(slide_info, level)
        validate_image_z(slide_info, z)
        validate_image_channels(slide_info, image_channels)
        if not settings.apply_padding or check_complete_region_overlap(slide_info, level, start_x, start_y, size_x, size_y):
            image_region = await slide.get_region(level, start_x, start_y, size_x, size_y,
                                                  padding_color=vp_color, z=z, icc_intent=apply_icc_intent)
        else:
            image_region = await get_extended_region(
                slide.get_region, slide_info, level, start_x, start_y, size_x, size_y,
                padding_color=vp_color, z=z, icc_intent=apply_icc_intent
            )
        return make_response(slide, image_region, image_format, image_quality, image_channels)

    @app.get(
        "/slides/tile/level/{level}/tile/{tile_x}/{tile_y}",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            slide_id=IdQuery,
            level: int = Path(ge=0, examples=[0], description="Pyramid level of region"),
            tile_x: int = Path(examples=[0], description="Request the tile_x-th tile in x dimension"),
            tile_y: int = Path(examples=[0], description="Request the tile_y-th tile in y dimension"),
            image_channels: List[int] = ImageChannelQuery,
            z: int = ZStackQuery,
            padding_color: str = ImagePaddingColorQuery,
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            apply_icc_intent: str = ICCProfileIntent,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
    ):
        """
        Get a tile of a slide given its ID and by providing the following parameters:

        * `level` - Pyramid level of the tile. Level 0 is highest (original) resolution.
        The available levels depend on the image.

        * `tile_x`, `tile_y` - Coordinates are given with respect to tiles,
        i.e. tile coordinate n is the n-th tile in the respective dimension.
        Coordinates are also given with respect to the requested level.
        Coordinates (0,0) select the tile at the upper left corner of the image.

        There are a number of addtional query parameters:

        * `image_channels` - Single channels (or multiple channels) can be retrieved through
        the optional parameter image_channels as an integer array referencing the channel IDs.
        This is paricularly important for images with abitrary image channels and channels
        with a higher color depth than 8bit (e.g. fluorescence images).
        The channel composition of the image can be obtained through the slide info endpoint,
        where the dedicated channels are listed along with its color, name and bitness.
        By default all channels are returned.

        * `z` - The region endpoint also offers the selection of a layer in a Z-Stack by setting the index z.
        Default is z=0.

        * `padding_color` - Background color as 24bit-hex-string with leading #,
        that is used when image tile contains whitespace when out of image extent. Default is white.
        Only works for 8-bit RGB slides, otherwise the background color is black.

        * `image_format` - The image format can be selected. Formats include jpeg, png, tiff, bmp, gif.
        When tiff is specified as output format the raw data of the image is returned.
        Multi-channel images can also be represented as RGB-images (mostly for displaying reasons in the viewer).
        Note that the mapping of all color channels to RGB values is currently restricted to the first three channels.
        Default is jpeg.

        * `image_quality` - The image quality can be set for specific formats,
        e.g. for the jpeg format a value between 0 and 100 can be selected. Default is 90.
        It is ignored if raw jpeg tiles are available through a WSI service plugin.
        """
        vp_color = validate_hex_color_string(padding_color)
        validate_image_request(image_format, image_quality)
        await api_integration.allow_access_slide(auth_payload=payload, slide_id=slide_id, manager=slide_manager,
                                                 plugin=plugin)
        slide = await slide_manager.get_slide(slide_id, plugin=plugin)
        slide_info = await slide.get_info()
        validate_image_level(slide_info, level)
        validate_image_z(slide_info, z)
        validate_image_channels(slide_info, image_channels)
        if not settings.apply_padding or check_complete_tile_overlap(slide_info, level, tile_x, tile_y):
            image_tile = await slide.get_tile(level, tile_x, tile_y, padding_color=vp_color, z=z, icc_intent=apply_icc_intent)
        else:
            image_tile = await get_extended_tile(
                slide.get_tile, slide_info, level, tile_x, tile_y, padding_color=vp_color, z=z, icc_intent=apply_icc_intent
            )
        return make_response(slide, image_tile, image_format, image_quality, image_channels)

    @app.get("/slides/download", tags=["Main Routes"])
    async def _(slide_id=IdQuery, plugin: str = PluginQuery, payload=api_integration.global_depends()):
        """
        Download raw slide data as zip
        """
        await api_integration.allow_access_slide(auth_payload=payload, slide_id=slide_id, manager=slide_manager,
                                                 plugin=plugin)
        paths = await slide_manager.get_slide_file_paths(slide_id)
        # Paths contain file paths that are stored in the storage mapper.
        # This sometimes does not include all files that are associated
        # with a slide, but only a folder, e.g. DICOM. These folders are
        # expanded to include the files they contain, and then removed.
        paths = remove_folders(expand_folders(paths))
        zf = ZipFly(paths=get_zipfly_paths(paths), chunksize="1_000_000")
        return StreamingResponse(
            zf.generator(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment;filename={slide_id}.zip",
            },
        )

    @app.get("/slides/icc_profile", tags=["Main Routes"])
    async def _(slide_id=IdQuery, plugin: str = PluginQuery, payload=api_integration.global_depends()):
        """
        Download icc profile for a slide
        """
        await api_integration.allow_access_slide(auth_payload=payload, slide_id=slide_id, manager=slide_manager,
                                                 plugin=plugin)
        slide = await slide_manager.get_slide(slide_id, plugin=plugin)
        profile = await slide.get_icc_profile()
        return make_response(slide, profile, "raw", None, None)

    ##
    # NEW API ALLOWING BATCH ACCESS
    ##
    @app.get("/files/info", response_model=List[SlideInfo], tags=["Main Routes"])
    async def _(paths: str = IdListQuery, plugin: str = PluginQuery, payload=api_integration.global_depends()):
        return await info(paths, plugin, payload, slide_manager)

    @app.get(
        "/files/thumbnail/max_size/{max_x}/{max_y}",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            paths: str = IdListQuery,
            max_x: int = Path(example=100, ge=1, le=settings.max_thumbnail_size,
                              description="Maximum width of thumbnail"),
            max_y: int = Path(example=100, ge=1, le=settings.max_thumbnail_size,
                              description="Maximum height of thumbnail"),
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            apply_icc_intent: str = ICCProfileIntent,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
    ):
        return await thumbnail(paths, max_x, max_y, image_format, image_quality, plugin, payload, slide_manager, apply_icc_intent)

    @app.get(
        "/files/label/max_size/{max_x}/{max_y}",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            paths: str = IdListQuery,
            max_x: int = Path(example=100, description="Maximum width of label image"),
            max_y: int = Path(example=100, description="Maximum height of label image"),
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
    ):
        return await label(paths, max_x, max_y, image_format, image_quality, plugin, payload, slide_manager)

    @app.get(
        "/files/macro/max_size/{max_x}/{max_y}",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            paths: str = IdListQuery,
            max_x: int = Path(example=100, description="Maximum width of macro image"),
            max_y: int = Path(example=100, description="Maximum height of macro image"),
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            apply_icc_intent: str = ICCProfileIntent,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
    ):
        return await macro(paths, max_x, max_y, image_format, image_quality, apply_icc_intent,
                           plugin, payload, slide_manager)

    @app.get(
        "/files/tile/level/{level}/tile/{tile_x}/{tile_y}",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            paths: str = IdListQuery,
            level: int = Path(ge=0, example=0, description="Pyramid level of region"),
            tile_x: int = Path(example=0, description="Request the tile_x-th tile in x dimension"),
            tile_y: int = Path(example=0, description="Request the tile_y-th tile in y dimension"),
            image_channels: List[int] = ImageChannelQuery,
            z: int = ZStackQuery,
            padding_color: str = ImagePaddingColorQuery,
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            apply_icc_intent: str = ICCProfileIntent,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
    ):
        return await tile(paths, level, tile_x, tile_y, image_channels, z, padding_color, image_format, image_quality,
                          apply_icc_intent, plugin, payload, slide_manager)


    # To allow for diverse regions etc..
    @app.get(
        "/files/batch/",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            paths: str = IdListQuery,
            levels: str = TileLevelListQuery,
            xs: str = TileXListQuery,
            ys: str = TileYListQuery,
            image_channels: List[int] = ImageChannelQuery,
            z: int = ZStackQuery,  # TODO also?
            padding_color: str = ImagePaddingColorQuery,
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            apply_icc_intent: str = ICCProfileIntent,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
    ):
        return await batch(paths, levels, xs, ys, image_channels, z, padding_color, image_format, image_quality,
                           apply_icc_intent, plugin, payload, slide_manager)

    @app.get("/files/icc_profile", tags=["Main Routes"])
    async def _(paths: str = IdListQuery, plugin: str = PluginQuery, payload=api_integration.global_depends()):
        """
        Download icc profile for a slide
        """
        return await icc_profile(paths, plugin, payload, slide_manager)

    #############################################
    # OLD ENDPOINTS FOR BACKWARDS COMPATIBILITY #
    #############################################
    @app.get("/batch/info", response_model=List[SlideInfo], tags=["Main Routes"])
    async def _(slides: str = IdListQuery2, plugin: str = PluginQuery, payload=api_integration.global_depends()):
        return await info(slides, plugin, payload, slide_manager)

    @app.get(
        "/batch/thumbnail/max_size/{max_x}/{max_y}",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            slides: str = IdListQuery2,
            max_x: int = Path(example=100, ge=1, le=settings.max_thumbnail_size,
                              description="Maximum width of thumbnail"),
            max_y: int = Path(example=100, ge=1, le=settings.max_thumbnail_size,
                              description="Maximum height of thumbnail"),
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            apply_icc_intent: str = ICCProfileIntent,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
    ):
        return await thumbnail(slides, max_x, max_y, image_format, image_quality, apply_icc_intent,
                               plugin, payload, slide_manager)

    @app.get(
        "/batch/label/max_size/{max_x}/{max_y}",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            slides: str = IdListQuery2,
            max_x: int = Path(example=100, description="Maximum width of label image"),
            max_y: int = Path(example=100, description="Maximum height of label image"),
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
    ):
        return await label(slides, max_x, max_y, image_format, image_quality, plugin, payload, slide_manager)

    @app.get(
        "/batch/macro/max_size/{max_x}/{max_y}",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            slides: str = IdListQuery2,
            max_x: int = Path(example=100, description="Maximum width of macro image"),
            max_y: int = Path(example=100, description="Maximum height of macro image"),
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            apply_icc_intent: str = ICCProfileIntent,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
    ):
        return await macro(slides, max_x, max_y, image_format, image_quality, apply_icc_intent,
                           plugin, payload, slide_manager)

    @app.get(
        "/batch/tile/level/{level}/tile/{tile_x}/{tile_y}",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            slides: str = IdListQuery2,
            level: int = Path(ge=0, example=0, description="Pyramid level of region"),
            tile_x: int = Path(example=0, description="Request the tile_x-th tile in x dimension"),
            tile_y: int = Path(example=0, description="Request the tile_y-th tile in y dimension"),
            image_channels: List[int] = ImageChannelQuery,
            z: int = ZStackQuery,
            padding_color: str = ImagePaddingColorQuery,
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            apply_icc_intent: str = ICCProfileIntent,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
    ):
        return await tile(slides, level, tile_x, tile_y, image_channels, z,
                          padding_color, image_format, image_quality, apply_icc_intent,
                          plugin, payload, slide_manager)

    @app.get(
        "/batch/batch/",
        responses=ImageResponses,
        response_class=StreamingResponse,
        tags=["Main Routes"],
    )
    async def _(
            slides: str = IdListQuery2,
            levels: str = TileLevelListQuery,
            xs: str = TileXListQuery,
            ys: str = TileYListQuery,
            image_channels: List[int] = ImageChannelQuery,
            z: int = ZStackQuery,  # TODO also?
            padding_color: str = ImagePaddingColorQuery,
            image_format: str = ImageFormatsQuery,
            image_quality: int = ImageQualityQuery,
            apply_icc_intent: str = ICCProfileIntent,
            plugin: str = PluginQuery,
            payload=api_integration.global_depends(),
    ):
        return await batch(slides, levels, xs, ys, image_channels, z, padding_color, image_format, image_quality,
                           apply_icc_intent, plugin, payload, slide_manager)

    @app.get("/batch/icc_profile", tags=["Main Routes"])
    async def _(paths: str = IdListQuery, plugin: str = PluginQuery, payload=api_integration.global_depends()):
        """
        Download icc profile for a slide
        """
        return await icc_profile(paths, plugin, payload, slide_manager)