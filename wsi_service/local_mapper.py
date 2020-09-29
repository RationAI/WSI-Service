import os

from openslide import OpenSlide
from fastapi import HTTPException
from uuid import uuid5, NAMESPACE_URL


class LocalMapper:
    def __init__(self, data_dir):
        self._initialize_with_path(data_dir)

    def _initialize_with_path(self, data_dir):
        self.case_map = {} # maps from case_id to list of slide ids
        self.slide_map = {} # maps from slide_id to path
        self._collect_all_folders_as_cases(data_dir)
        for case_id, case in self.case_map.items():
            case_dir = os.path.join(data_dir, case["local_case_id"])
            self._collect_all_files_as_slides(case_id, case_dir)
            

    def _collect_all_folders_as_cases(self, data_dir):
        for d in os.listdir(data_dir):
            absdir = os.path.join(data_dir, d)
            if os.path.isdir(absdir):
                case_id = uuid5(NAMESPACE_URL, d).hex
                self.case_map[case_id] = {'local_case_id': d, 'slides':[]}
    
    def _collect_all_files_as_slides(self, case_id, case_dir):
        for f in os.listdir(case_dir):
            absfile = os.path.join(case_dir, f)
            if OpenSlide.detect_format(absfile):
                raw_slide_id = os.path.splitext(f)[0]
                slide_id = uuid5(NAMESPACE_URL, raw_slide_id).hex
                if slide_id not in self.slide_map:
                    self.case_map[case_id]["slides"].append(slide_id)
                    self.slide_map[slide_id] = {
                        'global_case_id': case_id,
                        'storage_address': absfile, 
                        'global_slide_id': slide_id,
                        'local_slide_id': raw_slide_id,
                        'storage_type': "local",
                    }

    def get_cases(self):
        case_data = []
        for case_id, case in self.case_map.items():
            case_data.append({'global_case_id': case_id, 'local_case_id': case['local_case_id']})
        return case_data

    def get_slides(self, case_id):
        if case_id not in self.case_map:
            raise HTTPException(status_code=400, detail=f"Case with global_case_id {case_id} does not exist")
        slide_data = []
        for slide_id in sorted(self.case_map[case_id]['slides']):
            slide_data.append(self.slide_map[slide_id])
        return slide_data

    def get_slide(self, slide_id):
        if slide_id not in self.slide_map:
            raise HTTPException(status_code=400, detail=f"Slide with global_slide_id {slide_id} does not exist")
        return self.slide_map[slide_id]
