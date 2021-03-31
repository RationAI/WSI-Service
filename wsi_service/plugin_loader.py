import pathlib

plugin_directory = {}

try:
    from wsi_service.loader_plugins.deformation_plugin.deformed_slide import (
        DeformedSlide,
    )

    plugin_directory["sqreg"] = DeformedSlide
except ModuleNotFoundError:
    print("Cannot load DeformedSlide loader. Continuing without support for deformed slides.")
from wsi_service.loader_plugins.slide_dummy import DummySlide
from wsi_service.loader_plugins.slide_isyntax import IsyntaxSlide
from wsi_service.loader_plugins.slide_ometif import OmeTiffSlide
from wsi_service.loader_plugins.slide_openslide import OpenSlideSlide

plugin_directory[".ome.tiff"] = OmeTiffSlide
plugin_directory[".ome.tif"] = OmeTiffSlide
plugin_directory[".tiff"] = OpenSlideSlide
plugin_directory[".tif"] = OpenSlideSlide
plugin_directory[".mrxs"] = OpenSlideSlide
plugin_directory[".svs"] = OpenSlideSlide
plugin_directory[".ndpi"] = OpenSlideSlide
plugin_directory[".bif"] = OpenSlideSlide
plugin_directory[".scn"] = OpenSlideSlide
plugin_directory[".isyntax"] = IsyntaxSlide


def load_slide(filepath, slide_id, plugin_directory=plugin_directory):
    for extension in plugin_directory:
        if filepath.endswith(extension):
            return plugin_directory[extension](filepath, slide_id)
    return None
