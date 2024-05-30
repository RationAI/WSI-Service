import os
import pathlib

from wsi_service_plugin_tifffile_generic.slide import Slide

priority = 1


def is_supported(filepath):
    if os.path.isfile(filepath):
        filename = pathlib.Path(filepath).name
        for suffix in ["tif", "tiff"]:
            if filename.endswith(suffix):
                return True
    return False


async def open(filepath):
    return await Slide.create(filepath)
