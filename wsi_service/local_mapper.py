import glob
import hashlib
import os
import pickle
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from filelock import FileLock

from wsi_service.custom_models.local_mapper_models import CaseLocalMapper, SlideLocalMapper
from wsi_service.models.v3.storage import SlideStorage, StorageAddress
from wsi_service.plugins import is_supported_format


class LocalMapper:
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
                self._initialize_with_path(self.data_dir)
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

    def _initialize_with_path(self, data_dir):
        self.case_map = {}
        self.slide_map = {}
        try:
            self._collect_all_folders_as_cases(data_dir)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=f"No such directory: {data_dir}") from e
        for case_id, case in self.case_map.items():
            case_dir = os.path.join(data_dir, case.local_id)
            self._collect_all_files_as_slides(data_dir, case_id, case_dir)

    def _collect_all_folders_as_cases(self, data_dir):
        for sub_data_dir in os.listdir(data_dir):
            absdir = os.path.join(data_dir, sub_data_dir)
            if os.path.isdir(absdir):
                case_id = uuid5(NAMESPACE_URL, sub_data_dir).hex
                self.case_map[case_id] = CaseLocalMapper(id=case_id, local_id=sub_data_dir, slides=[])

    def _collect_all_files_as_slides(self, data_dir, case_id, case_dir):
        local_case_id = self.case_map[case_id].local_id
        for case_file in os.listdir(case_dir):
            absfile = os.path.join(case_dir, case_file)
            if is_supported_format(absfile):
                slide_id = uuid5(NAMESPACE_URL, local_case_id + case_file).hex
                if slide_id not in self.slide_map:
                    self.case_map[case_id].slides.append(slide_id)
                    address = absfile.replace(data_dir + "/", "")
                    assocaited_storage_addresses = self._get_assocaited_storage_addresses(absfile, data_dir, slide_id)
                    self.slide_map[slide_id] = SlideLocalMapper(
                        id=slide_id,
                        local_id=case_file,
                        slide_storage=SlideStorage(
                            slide_id=slide_id,
                            storage_type="fs",
                            storage_addresses=[
                                StorageAddress(
                                    address=address,
                                    main_address=True,
                                    storage_address_id=slide_id,
                                    slide_id=slide_id,
                                )
                            ]
                            + assocaited_storage_addresses,
                        ),
                    )

    def _get_assocaited_storage_addresses(self, absfile, data_dir, slide_id):
        assocaited_storage_addresses = []
        if absfile.endswith(".mrxs"):
            files = glob.glob(os.path.join(absfile.replace(".mrxs", ""), "*"))
            for f in files:
                address = f.replace(data_dir + "/", "")
                assocaited_storage_addresses.append(
                    StorageAddress(
                        address=f.replace(data_dir + "/", ""),
                        main_address=False,
                        storage_address_id=uuid5(NAMESPACE_URL, slide_id + address).hex,
                        slide_id=slide_id,
                    )
                )
        return assocaited_storage_addresses

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
