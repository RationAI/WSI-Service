import os
import pathlib

from wsi_service_plugin_tiffslide.slide import Slide

priority = 1


def is_supported(filepath):
    if os.path.isfile(filepath):
        filename = pathlib.Path(filepath).name
        suffix = pathlib.Path(filepath).suffix
        if filename.endswith("ome.tif") or filename.endswith("ome.tiff"):
            return False
        return suffix in [".svs", ".tiff", ".tif"]
    else:
        return False


async def open(filepath):
    return await Slide.create(filepath)
