from typing import List

from pydantic import BaseModel

from wsi_service.models.commons import ServiceStatus


class PluginInfo(BaseModel):
    name: str
    version: str
    supported_file_extensions: List[str]


class WSIServiceStatus(ServiceStatus):
    plugins: List[PluginInfo]
    plugins_default: dict
