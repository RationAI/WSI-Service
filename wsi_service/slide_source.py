import atexit
import os
from threading import Lock, Timer

from werkzeug.exceptions import NotFound

from openslide import OpenSlide
from wsi_service.slide import Slide
from wsi_service.utils import sanitize_id


class ExpiringSlide:
    def __init__(self, slide, timer):
        self.slide = slide
        self.timer = timer


class SlideSource:

    def __init__(self, data_dir, timeout):
        atexit.register(self.close)
        self.lock = Lock()
        self._initialize_with_path(data_dir)
        self.opened_slides = {}
        self.timeout = timeout

    def close(self):
        for slide_id in list(self.opened_slides.keys()):
            self.opened_slides[slide_id].timer.cancel()
            self._close_slide(slide_id)


    def _initialize_with_path(self, data_dir):
        self.case_map = {} # maps from case_id to list of slide ids
        self.slide_map = {} # maps from slide_id to path
        # collect all folders as cases, all files in folders as slides
        for d in os.listdir(data_dir):
            absdir = os.path.join(data_dir, d)
            if os.path.isdir(absdir):
                case_id = sanitize_id(d)
                self.case_map[case_id] = []

                for f in os.listdir(absdir):
                    absfile = os.path.join(absdir, f)
                    if OpenSlide.detect_format(absfile):
                        raw_slide_id = os.path.splitext(f)[0]
                        slide_id = sanitize_id("%s_%s" % (case_id, raw_slide_id))
                        # if we have a slide id collision, ignore
                        if slide_id not in self.slide_map:
                            self.case_map[case_id].append(slide_id)
                            self.slide_map[slide_id] = {'path': absfile, 'raw_slide_id': raw_slide_id}

    # returns list of dict
    def get_cases(self):
        return sorted(list(self.case_map.keys()))

    # returns list of dict
    def get_slides(self, case_id):
        try:
            return sorted(self.case_map[case_id])
        except KeyError:
            raise NotFound()


    def get_slide(self, slide_id):
        with self.lock:
            if not slide_id in self.opened_slides:
                try:
                    path = self.slide_map[slide_id]['path']
                    slide = Slide(OpenSlide(path))
                    self.opened_slides[slide_id] = ExpiringSlide(slide, None)
                except KeyError:
                    raise NotFound()
            
            # reset slide expiration
            expiringSlide = self.opened_slides[slide_id]
            if expiringSlide.timer is not None:
                expiringSlide.timer.cancel()
            expiringSlide.timer = Timer(self.timeout, self._close_slide, [slide_id])
            expiringSlide.timer.start()
        
        return self.opened_slides[slide_id].slide
        
    def _close_slide(self, slide_id):
        with self.lock:
            if slide_id in self.opened_slides:
                self.opened_slides[slide_id].slide.close()
                del self.opened_slides[slide_id]
