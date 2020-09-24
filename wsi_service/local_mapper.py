import atexit
import os
from threading import Lock, Timer

from werkzeug.exceptions import NotFound

from openslide import OpenSlide
from wsi_service.slide import Slide
from wsi_service.utils import sanitize_id
from uuid import uuid5, NAMESPACE_URL


class LocalMapper:

    def __init__(self, data_dir):
        self._initialize_with_path(data_dir)


    def _initialize_with_path(self, data_dir):
        self.case_map = {} # maps from case_id to list of slide ids
        self.slide_map = {} # maps from slide_id to path
        # collect all folders as cases, all files in folders as slides
        for d in os.listdir(data_dir):
            absdir = os.path.join(data_dir, d)
            if os.path.isdir(absdir):
                case_id = uuid5(NAMESPACE_URL, d).hex
                self.case_map[case_id] = {'local_case_id': d, 'slides':[]}
                for f in os.listdir(absdir):
                    absfile = os.path.join(absdir, f)
                    if OpenSlide.detect_format(absfile):
                        raw_slide_id = os.path.splitext(f)[0]
                        slide_id = uuid5(NAMESPACE_URL, raw_slide_id).hex
                        # if we have a slide id collision, ignore
                        if slide_id not in self.slide_map:
                            self.case_map[case_id]["slides"].append(slide_id)
                            self.slide_map[slide_id] = {
                                'global_case_id': case_id,
                                'storage_address': absfile, 
                                'global_slide_id': slide_id,
                                'local_slide_id': raw_slide_id,
                                'storage_type': "local",
                                }

    # returns list of dict
    def get_cases(self):
        return sorted(list(self.case_map.keys()))

    # returns list of dict
    def get_slides(self, case_id):
        try:
            slide_data = []
            for slide_id in sorted(self.case_map[case_id]['slides']):
                slide_data.append(self.slide_map[slide_id])
            return slide_data
        except KeyError:
            raise NotFound()


    def get_slide(self, slide_id):
        return self.slide_map[slide_id]
        
