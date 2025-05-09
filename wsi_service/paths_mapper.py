import os

from fastapi import HTTPException


from wsi_service.custom_models.local_mapper_models import SlideLocalMapper
from wsi_service.custom_models.old_v3.storage import SlideStorage
from wsi_service.plugins import is_supported_format
from wsi_service.utils.app_utils import local_mode_collect_secondary_files_v3


# File paths mapper that expects file paths in path>to>file instead of path/to/file
#  (URL compatibility reasons)
class PathsMapper:
    def __init__(self, data_dir):
        self.data_dir = data_dir

    def refresh(self, force_refresh=True):
        ...

    def load(self):
        ...

    def get_cases(self):
        # cases not supported, only direct access
        return []

    def get_slides(self, case_id):
        # cases not supported, only direct access
        return []

    def get_slide(self, slide_id):
        slide_id = slide_id.replace('>', '/')
        absfile = os.path.join(self.data_dir, slide_id)
        if not is_supported_format(absfile):
            raise HTTPException(status_code=404, detail=f"Slide {slide_id} does not exist")

        addresses = local_mode_collect_secondary_files_v3(absfile, slide_id, slide_id, self.data_dir)
        return SlideLocalMapper(
            id=slide_id,
            local_id=slide_id,
            slide_storage=SlideStorage(
                slide_id=slide_id,
                storage_type="fs",
                storage_addresses=addresses,
            )
        )