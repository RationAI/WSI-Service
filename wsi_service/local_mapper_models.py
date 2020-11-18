from typing import List

from pydantic import BaseModel


class StorageAddress(BaseModel):
    storage_address_id: str
    slide_id: str
    address: str
    main_address: bool


class SlideStorage(BaseModel):
    slide_id: str
    storage_type: str
    storage_addresses: List[StorageAddress]


class SlideLocalMapper(BaseModel):
    slide_id: str
    local_slide_id: str
    slide_storage: SlideStorage


class CaseLocalMapper(BaseModel):
    case_id: str
    local_case_id: str
    slides: List[str]
