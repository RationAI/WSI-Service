from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from wsi_service.api.root import add_routes_root
from wsi_service.api.v1 import add_routes_v1
from wsi_service.api.v3 import add_routes_v3
from wsi_service.singletons import settings
from wsi_service.slide_manager import SlideManager

openapi_url = "/openapi.json"
if settings.disable_openapi:
    openapi_url = ""

slide_manager = SlideManager(
    settings.mapper_address,
    settings.data_dir,
    settings.inactive_histo_image_timeout_seconds,
    settings.image_handle_cache_size,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    slide_manager.close()


app = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json" if not settings.disable_openapi else "",
    root_path=settings.root_path,
    lifespan=lifespan,
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

add_routes_v1(app_v1, settings, slide_manager)
add_routes_v3(app_v3, settings, slide_manager)

app.mount("/v1", app_v1)
app.mount("/v3", app_v3)
