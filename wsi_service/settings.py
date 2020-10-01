from pydantic import BaseSettings

from wsi_service.version import __version__


class Settings(BaseSettings):
    title: str = "WSI Service"
    description: str = "EMPAIA WSI Service to stream whole slide images"
    version: str = __version__

    data_dir: str
    mapper_address: str
    local_mode: bool
    inactive_histo_image_timeout_seconds: int = 600
    max_returned_region_size: int = 6250000  # 2500 x 2500
