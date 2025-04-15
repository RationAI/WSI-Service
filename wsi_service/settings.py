from typing import Set

from pydantic_settings import BaseSettings, SettingsConfigDict

from wsi_service.version import __version__


class Settings(BaseSettings):
    title: str = "WSI Service"
    description: str = "EMPAIA WSI Service to stream whole slide images"
    version: str = __version__

    # Auth
    connection_chunk_size: int = 1024000
    connection_limit_per_host: int = 100
    http_client_timeout: int = 300
    request_timeout: int = 300
    api_v3_integration: str = ""
    idp_url: str = ""
    client_id: str = ""
    client_secret: str = ""
    organization_id: str = ""

    disable_openapi: bool = False
    cors_allow_credentials: bool = False
    cors_allow_origins: Set[str] = set()
    debug: bool = False
    data_dir: str = "/data"
    mapper_address: str = "http://localhost:8080/v3/slides/{slide_id}/storage"
    local_mode: str = ""  # path to a class that implements local mode
    enable_local_routes: bool = True
    enable_viewer_routes: bool = True
    inactive_histo_image_timeout_seconds: int = 600
    image_handle_cache_size: int = 50
    max_returned_region_size: int = 25_000_000  # e.g. 5000 x 5000
    max_thumbnail_size: int = 500
    root_path: str = ""

    # Todo: batch queries do not apply padding - implement or document
    # default color for padding of image regions out of image extent
    padding_color: tuple = (255, 255, 255)
    apply_padding: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="ws_", extra="ignore")
