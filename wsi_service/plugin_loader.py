import pathlib

from wsi_service.loader_plugins.slide_dummy import DummySlide
from wsi_service.loader_plugins.slide_openslide import OpenSlideSlide

plugin_directory = {
    ".tiff": OpenSlideSlide,
    ".mrxs": OpenSlideSlide,
    ".svs": OpenSlideSlide,
    ".ndpi": OpenSlideSlide,
}


def load_slide(filepath, slide_id, plugin_directory=plugin_directory):
    file_extension = pathlib.Path(filepath).suffix
    return plugin_directory[file_extension](filepath, slide_id)
