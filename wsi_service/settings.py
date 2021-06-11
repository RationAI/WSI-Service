from typing import Set

from pydantic import BaseSettings

from wsi_service.version import __version__


class Settings(BaseSettings):
    title: str = "WSI Service"
    description: str = "EMPAIA WSI Service to stream whole slide images"
    version: str = __version__
    disable_openapi: bool = False
    cors_allow_origins: Set[str] = None

    isyntax_port: int = 5556
    debug: bool = False
    data_dir: str = None
    mapper_address: str = None
    local_mode: bool = False
    inactive_histo_image_timeout_seconds: int = 600
    max_returned_region_size: int = 4 * 6250000  # 5000 x 5000
    root_path: str = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "ws_"
