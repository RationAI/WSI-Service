from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from wsi_service.api.root import add_routes_root
from wsi_service.api.v3 import add_routes_v3
from wsi_service.singletons import settings
from wsi_service.slide_manager import SlideManager
from wsi_service.plugins import plugins
from wsi_service.singletons import logger

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
    logger.info("🚀 LIFESPAN: startup")
    for plugin_name, plugin in plugins.items():
        if hasattr(plugin, "start") and callable(getattr(plugin, "start")):
            plugin.start()

    yield

    logger.info("💥 LIFESPAN: shutdown")
    for plugin_name, plugin in plugins.items():
        if hasattr(plugin, "stop") and callable(getattr(plugin, "stop")):
            plugin.stop()
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
    debug=settings.debug
)

add_routes_root(app, settings)

app_v3 = FastAPI(openapi_url=openapi_url)

if settings.cors_allow_origins:
    for app_obj in [app, app_v3]:
        app_obj.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )

add_routes_v3(app_v3, settings, slide_manager)

app.mount("/v3", app_v3)
