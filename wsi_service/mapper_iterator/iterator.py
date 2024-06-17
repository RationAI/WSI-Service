import hashlib
import os
import pickle
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from filelock import FileLock

from wsi_service.custom_models.local_mapper_models import CaseLocalMapper, SlideLocalMapper
from wsi_service.custom_models.old_v3.storage import SlideStorage, StorageAddress
from wsi_service.plugins import is_supported_format

from .iterator.settings import SettingsIterator
from .iterator.iterator import iterate

class IteratorMapper:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.hash = None
        self.case_map = {}
        self.slide_map = {}
        self.refresh(force_refresh=False)

    def refresh(self, force_refresh=True):
        with FileLock("local_mapper.lock"):
            data_dir_changed = self._get_data_dir_changed()
            if force_refresh or data_dir_changed or not os.path.exists("local_mapper.p"):
                settings = SettingsIterator()
                settings.source_path = self.data_dir
                cases, slides = iterate(settings)
                self.case_map = cases
                self.slide_map = slides
                data = {}
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
