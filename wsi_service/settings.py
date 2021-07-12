from typing import Set

from pydantic import BaseSettings

from wsi_service.version import __version__


class Settings(BaseSettings):
    title: str = "WSI Service"
    description: str = "EMPAIA WSI Service to stream whole slide images"
    version: str = __version__

    disable_openapi: bool = False
    cors_allow_origins: Set[str] = None
    data_dir: str = "/data"
    mapper_address: str = None
    local_mode: bool = False
    inactive_histo_image_timeout_seconds: int = 600
    max_returned_region_size: int = 4 * 6250000  # 5000 x 5000
    max_thumbnail_size: int = 500
    root_path: str = None

    # define plugin defaults for specific formats
    plugins_default = {".tiff": "openslide", ".tif": "openslide"}

    # default color for padding of image regions out of image extent
    padding_color = (255, 255, 255)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "ws_"
