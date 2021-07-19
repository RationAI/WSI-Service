import os
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException

from wsi_service.local_mapper_models import CaseLocalMapper, SlideLocalMapper
from wsi_service.models.storage import SlideStorage, StorageAddress
from wsi_service.plugins import is_supported_format


class LocalMapper:
    def __init__(self, data_dir):
        self._initialize_with_path(data_dir)

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
        for case_file in os.listdir(case_dir):
            absfile = os.path.join(case_dir, case_file)
            if is_supported_format(absfile):
                slide_id = uuid5(NAMESPACE_URL, case_file).hex
                if slide_id not in self.slide_map:
                    self.case_map[case_id].slides.append(slide_id)
                    address = absfile.replace(data_dir + "/", "")
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
                                    storage_address_id=uuid5(NAMESPACE_URL, address).hex,
                                    slide_id=slide_id,
                                )
                            ],
                        ),
                    )

    def get_cases(self):
        return list(self.case_map.values())

    def get_slides(self, case_id):
        if case_id not in self.case_map:
            raise HTTPException(status_code=404, detail=f"Case with case_id {case_id} does not exist")
        slide_data = []
        for slide_id in sorted(self.case_map[case_id].slides):
            slide_data.append(self.slide_map[slide_id])
        return slide_data

    def get_slide(self, slide_id):
        if slide_id not in self.slide_map:
            raise HTTPException(status_code=404, detail=f"Slide with slide_id {slide_id} does not exist")
        return self.slide_map[slide_id]
