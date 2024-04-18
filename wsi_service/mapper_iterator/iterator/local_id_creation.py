import os
import re
import uuid
from wsi_service.custom_models.local_mapper_models import CaseLocalMapper, SlideLocalMapper
from wsi_service.models.v3.storage import SlideStorage, StorageAddress


class IteratedCaseLocalMapper(CaseLocalMapper):
    institution: str
    project: str
    context_id: str
    namespace: str
    path: str
    to_import: bool


class IteratedSlideLocalMapper(SlideLocalMapper):
    institution: str
    project: str
    context_id: str
    to_import: bool

def create_case_object(settings, source_path):
    context_id = os.path.basename(source_path)
    path = str(source_path)
    institution = "anononymized"
    project = "anononymized"
    type = "w"

    if settings.institution_pattern != "":
        institution_match = re.search(settings.institution_pattern, str(source_path))
        if institution_match is not None:
            institution = institution_match.group()
            assert len(institution) <= 4
    if settings.project_pattern != "":
        project_patterns = re.search(settings.project_pattern, str(source_path))
        if project_patterns != []:
            project = str(project[-1])
            assert len(project) <= 4

    namespace = uuid.uuid5(uuid.NAMESPACE_DNS, path)
    local_id = institution + "." + project + "." + type + "." + context_id
    case = IteratedCaseLocalMapper(
        id=local_id,
        context_id=context_id,
        namespace=namespace,
        path=path,
        institution=institution,
        project=project,
        local_id=local_id,
        slides=[],
        to_import=True,
    )
    return case


def create_slide_object(file_path, case):
    file_name = os.path.basename(file_path)
    slide_local_id = uuid.uuid5(case.id, file_path)
    type = "w"

    local_id = case.institution + "." + case.project + "." + type + "." + slide_local_id,

    slide = IteratedSlideLocalMapper(
        id=local_id,
        context_id=slide_local_id,
        local_id=case.institution + "." + case.project + "." + type + "." + slide_local_id,
        case_local_id=case.local_id,
        institution=case.institution,
        project=case.project,
        to_import=True,
        slide_storage=SlideStorage(
            slide_id=local_id,
            storage_type="fs",
            storage_addresses=[
                StorageAddress(
                    address=file_path,
                    main_address=True,
                    storage_address_id=local_id,
                    slide_id=local_id,
                )
            ],
        ),
    )
    return slide
