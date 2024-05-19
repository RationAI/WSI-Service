import hashlib
import os
import pickle
import uuid
import csv

from fastapi import HTTPException
from filelock import FileLock
from pydantic_settings import BaseSettings, SettingsConfigDict

from wsi_service.custom_models.local_mapper_models import CaseLocalMapper, SlideLocalMapper
from wsi_service.custom_models.old_v3.storage import SlideStorage, StorageAddress


class CSVMapperSettings(BaseSettings):
    source: str = 'data.csv'
    separator: str = '\t'
    institution: int = 0
    project: int = 1
    slide_id: int = 2
    case_id: int = 3
    path: int = 4

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="csws_"
    )


class IteratedCaseLocalMapper(CaseLocalMapper):
    institution: str
    project: str
    context_id: str
    namespace: uuid.UUID
    to_import: bool


class IteratedSlideLocalMapper(SlideLocalMapper):
    institution: str
    project: str
    context_id: str
    to_import: bool


def create_case_object(settings, row):
    context_id = row[settings.case_id]
    institution = row[settings.institution]
    project = row[settings.project]
    type = "c"

    # todo pydantic
    assert len(project) <= 5
    assert len(institution) <= 5

    namespace = uuid.uuid5(uuid.NAMESPACE_DNS, context_id)
    local_id = institution + "." + project + "." + type + "." + context_id
    case = IteratedCaseLocalMapper(
        id=local_id,
        context_id=context_id,
        namespace=namespace,
        institution=institution,
        project=project,
        local_id=local_id,
        slides=[],
        to_import=True,
    )
    return case


def create_slide_object(settings, case, row):
    slide_local_id = row[settings.slide_id]
    type = "w"

    local_id = case.institution + "." + case.project + "." + type + "." + str(slide_local_id)

    slide = IteratedSlideLocalMapper(
        id=local_id,
        context_id=str(slide_local_id),
        local_id=local_id,
        case_local_id=case.local_id,
        institution=case.institution,
        project=case.project,
        to_import=True,
        slide_storage=SlideStorage(
            slide_id=local_id,
            storage_type="fs",
            storage_addresses=[
                StorageAddress(
                    address=row[settings.path],
                    main_address=True,
                    storage_address_id=local_id,
                    slide_id=local_id,
                )
            ],
        ),
    )
    return slide


class CSVMapper:
    """
    CSV Mapper will read CSV file definitions: (indexes are configurable)
    INSTITUTION   PROJECT     SLIDE_ID     CASE        PATH
    <ID>          <VALUE>     <ID>         <CASE_ID>   <WSI-PATH>

    The slide ID will be created as such:   institution.project.w.slide_id
    and mapped to the given path of the slide, which must be relative to the server root!
    All slides that belong to the same case must specify case id, which will be created as
    institution.project.c.case_id (of the first institution/project found). All slides
    of a case should be within same project and institution.
    """

    def __init__(self, data_dir):
        self.settings = CSVMapperSettings()
        self.data_dir = data_dir
        self.hash = None
        self.case_map = {}
        self.slide_map = {}
        self.refresh(force_refresh=False)

    def refresh(self, force_refresh=True):
        with FileLock("local_mapper.lock"):
            data_dir_changed = self._get_data_dir_changed()
            if force_refresh or data_dir_changed or not os.path.exists("local_mapper.p"):
                data = {}
                try:
                    self._read_csv_data()
                except Exception as e:
                    raise HTTPException(500, "Failed to parse the CSV file! Is your syntax correct?") from e

                data["data_dir"] = self.data_dir
                data["case_map"] = self.case_map
                data["slide_map"] = self.slide_map
                with open("local_mapper.p", "wb") as f:
                    pickle.dump(data, f)
        self.load()

    def load(self):
        updated_hash = self._get_updated_hash()
        if self.hash != updated_hash:
            with FileLock("local_mapper.lock"):
                with open("local_mapper.p", "rb") as f:
                    data = pickle.load(f)
                    self.case_map = data["case_map"]
                    self.slide_map = data["slide_map"]
                self.hash = self._get_updated_hash()

    def _read_csv_data(self):
        settings = self.settings
        self.case_map = {}
        self.slide_map = {}
        with open(self.settings.source, 'r') as file:
            reader = csv.reader(file, delimiter='\t')
            for data in reader:
                case_id = data[settings.case_id]
                case = self.case_map.get(case_id, None)
                if case is None:
                    case = create_case_object(settings=settings, row=data)
                    self.case_map[case.id] = case
                slide = create_slide_object(settings=settings, case=case, row=data)
                case.slides.append(slide.id)
                self.slide_map[slide.id] = slide

    def _get_updated_hash(self):
        return hashlib.md5(open("local_mapper.p", "rb").read()).hexdigest()

    def _get_data_dir_changed(self):
        data_dir_changed = False
        if os.path.exists("local_mapper.p"):
            with open("local_mapper.p", "rb") as f:
                data = pickle.load(f)
                data_dir_changed = data["data_dir"] != self.data_dir
        return data_dir_changed

    def get_cases(self):
        self.load()
        return list(self.case_map.values())

    def get_slides(self, case_id):
        self.load()
        if case_id not in self.case_map:
            raise HTTPException(status_code=404, detail=f"Case with case_id {case_id} does not exist")
        slide_data = []
        for slide_id in sorted(self.case_map[case_id].slides):
            slide_data.append(self.slide_map[slide_id])
        return slide_data

    def get_slide(self, slide_id):
        if slide_id not in self.slide_map:
            self.load()
            if slide_id not in self.slide_map:
                raise HTTPException(status_code=404, detail=f"Slide with slide_id {slide_id} does not exist")
        return self.slide_map[slide_id]
