import pathlib

from wsi_service.loader_plugins.slide_dummy import DummySlide
from wsi_service.loader_plugins.slide_ometif import OmeTiffSlide
from wsi_service.loader_plugins.slide_openslide import OpenSlideSlide

plugin_directory = {
    ".ome.tiff": OmeTiffSlide,
    ".ome.tif": OmeTiffSlide,
    ".tiff": OpenSlideSlide,
    ".mrxs": OpenSlideSlide,
    ".svs": OpenSlideSlide,
    ".ndpi": OpenSlideSlide,
    # ".tiff": OmeTiffSlide,
    # ".tif": OmeTiffSlide,
}


def load_slide(filepath, slide_id, plugin_directory=plugin_directory):
    for extension in plugin_directory:
        if filepath.endswith(extension):
            return plugin_directory[extension](filepath, slide_id)
    return None
