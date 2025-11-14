import os

from fastapi import HTTPException

from wsi_service.base_mapper import BaseMapper
from wsi_service.custom_models.local_mapper_models import CaseLocalMapper, SlideLocalMapper
from wsi_service.custom_models.old_v3.storage import SlideStorage
from wsi_service.plugins import is_supported_format
from wsi_service.utils.app_utils import local_mode_collect_secondary_files_v3


class PathsMapper(BaseMapper):
    """
    Mapper that exposes the directory structure of the data directory.

    The `context` parameter represents a relative path inside `data_dir`.
    It may use "/" (preferred) or ">" (fallback compatibility, is converted to "/") as a separator.
    """

    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.is_context_dependent = True

    def get_cases(self, context=None):
        if context is None:
            raise HTTPException(status_code=404, detail="context is required")

        context_path = context.replace(">", "/")
        abs_context_path = os.path.join(self.data_dir, context_path)

        if not os.path.isdir(abs_context_path):
            raise HTTPException(status_code=404, detail=f"Context folder '{context}' not found")

        subdirs = [d for d in os.listdir(abs_context_path) if os.path.isdir(os.path.join(abs_context_path, d))]

        cases = []
        for d in subdirs:
            case_id = f"{context}/{d}"
            case_path = os.path.join(abs_context_path, d)

            slide_ids = []
            for file in os.listdir(case_path):
                absfile = os.path.join(case_path, file)
                if os.path.isfile(absfile) and is_supported_format(absfile):
                    slide_ids.append(f"{case_id}/{file}")

            cases.append(
                CaseLocalMapper(
                    id=case_id,
                    local_id=case_id,
                    slides=slide_ids,
                )
            )

        return cases

    def get_slides(self, case_id):
        case_path = case_id.replace(">", "/")
        abs_case_path = os.path.join(self.data_dir, case_path)

        if not os.path.isdir(abs_case_path):
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

        slides = []
        for file in sorted(os.listdir(abs_case_path)):
            absfile = os.path.join(abs_case_path, file)
            if not os.path.isfile(absfile):
                continue
            if is_supported_format(absfile):
                slide_id = f"{case_id}/{file}"
                addresses = local_mode_collect_secondary_files_v3(absfile, slide_id, slide_id, self.data_dir)
                slides.append(
                    SlideLocalMapper(
                        id=slide_id,
                        local_id=file,
                        slide_storage=SlideStorage(slide_id=slide_id, storage_type="fs", storage_addresses=addresses),
                    ),
                )

        return slides

    def get_slide(self, slide_id):
        slide_id = slide_id.replace(">", "/")
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
            ),
        )
