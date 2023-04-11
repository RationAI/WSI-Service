import glob
import os
import pathlib

from wsi_service_plugin_openslide.slide import Slide


def is_supported(filepath):
    if os.path.isfile(filepath):
        return pathlib.Path(filepath).suffix in [".bif", ".mrxs", ".ndpi", ".scn", ".svs", ".tiff", ".tif"]
    else:
        return len(glob.glob(os.path.join(filepath, "*.vsf"))) > 0


async def open(filepath):
    return await Slide.create(filepath)
