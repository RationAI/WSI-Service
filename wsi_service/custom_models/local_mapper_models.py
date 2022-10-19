from typing import List

from pydantic import BaseModel

from wsi_service.models.v3.storage import SlideStorage


class CaseLocalMapper(BaseModel):
    id: str
    local_id: str
    slides: List[str]


class SlideLocalMapper(BaseModel):
    id: str
    local_id: str
    slide_storage: SlideStorage
