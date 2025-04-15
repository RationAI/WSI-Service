import os
import pathlib

from wsi_service_plugin_openslide.slide import Slide


def is_supported(filepath):
    if os.path.isfile(filepath):
        filename = pathlib.Path(filepath).name
        suffix = pathlib.Path(filepath).suffix
        if filename.endswith("ome.tif") or filename.endswith("ome.tiff"):
            return False
        return suffix in [".bif", ".mrxs", ".ndpi", ".scn", ".svs", ".tiff", ".tif", ".czi"]
    # VSF is not supported
    else:
    #     return any(list(pathlib.Path(filepath).glob("*.vsf")))
        return any(list(pathlib.Path(filepath).glob("*.dcm")))

async def open(filepath):
    return await Slide.create(filepath)
