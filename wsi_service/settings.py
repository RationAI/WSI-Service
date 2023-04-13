from typing import Set

from pydantic import BaseSettings

from wsi_service.version import __version__


class Settings(BaseSettings):
    title: str = "WSI Service"
    description: str = "EMPAIA WSI Service to stream whole slide images"
    version: str = __version__

    disable_openapi: bool = False
    cors_allow_credentials: bool = False
    cors_allow_origins: Set[str] = None
    debug: bool = False
    data_dir: str = "/data"
    mapper_address: str = "http://localhost:8080/slides/{slide_id}/storage"
    local_mode: bool = True
    enable_viewer_routes: bool = True
    inactive_histo_image_timeout_seconds: int = 600
    image_handle_cache_size: int = 50
    max_returned_region_size: int = 25_000_000  # e.g. 5000 x 5000
    max_thumbnail_size: int = 500
    root_path: str = None

    # default color for padding of image regions out of image extent
    padding_color = (255, 255, 255)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "ws_"
