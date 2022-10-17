import os
import pathlib
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from wsi_service.api.root import add_routes_root
from wsi_service.api.v1 import add_routes_v1
from wsi_service.api.v3 import add_routes_v3
from wsi_service.local_mapper import LocalMapper
from wsi_service.local_mapper_models import CaseLocalMapper, SlideLocalMapper, SlideStorage
from wsi_service.singletons import settings
from wsi_service.slide_manager import SlideManager

openapi_url = "/openapi.json"
if settings.disable_openapi:
    openapi_url = ""

app = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json" if not settings.disable_openapi else "",
    root_path=settings.root_path,
)

add_routes_root(app, settings)

app_v1 = FastAPI(openapi_url=openapi_url)
app_v3 = FastAPI(openapi_url=openapi_url)

if settings.cors_allow_origins:
    for app_obj in [app, app_v1, app_v3]:
        app_obj.add_middleware(
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

add_routes_v1(app_v1, settings, slide_manager)
add_routes_v3(app_v3, settings, slide_manager)

app.mount("/v1", app_v1)
app.mount("/v3", app_v3)


@app.on_event("shutdown")
async def shutdown_event():
    slide_manager.close()


if settings.local_mode:
    localmapper = LocalMapper(settings.data_dir)

    @app.get("/v1/cases/", response_model=List[CaseLocalMapper], tags=["Additional Routes (Standalone WSI Service)"])
    async def get_cases():
        """
        (Only in standalone mode) Browse the local directory and return case ids for each available directory.
        """
        cases = localmapper.get_cases()
        return cases

    @app.get(
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

    @app.get(
        "/v1/slides/{slide_id}", response_model=SlideLocalMapper, tags=["Additional Routes (Standalone WSI Service)"]
    )
    async def get_slide(slide_id: str):
        """
        (Only in standalone mode) Return slide data for a given slide ID.
        """
        slide = localmapper.get_slide(slide_id)
        return slide

    @app.get(
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

    @app.get("/v1/refresh_local_mapper", tags=["Additional Routes (Standalone WSI Service)"])
    async def refresh_local_mapper():
        """
        (Only in standalone mode) Refresh available files by scanning for new files.
        """
        localmapper.refresh()
        return JSONResponse({"detail": "Local mapper has been refreshed."}, status_code=200)


if settings.enable_viewer_routes:

    @app.get("/v1/slides/{slide_id}/viewer", response_class=HTMLResponse, include_in_schema=False)
    async def viewer(slide_id: str):
        viewer_html = open(
            os.path.join(pathlib.Path(__file__).parent.absolute(), "viewer.html"), "r", encoding="utf-8"
        ).read()
        viewer_html = viewer_html.replace("REPLACE_SLIDE_ID", slide_id)
        return viewer_html


if settings.enable_viewer_routes and settings.local_mode:

    @app.get("/v1/validation_viewer", response_class=HTMLResponse, include_in_schema=False)
    async def validation_viewer():
        validation_viewer_html = open(
            os.path.join(pathlib.Path(__file__).parent.absolute(), "validation_viewer.html"), "r", encoding="utf-8"
        ).read()
        return validation_viewer_html
