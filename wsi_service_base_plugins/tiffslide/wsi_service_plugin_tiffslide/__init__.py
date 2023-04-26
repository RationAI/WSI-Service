import pathlib

from wsi_service_plugin_tiffslide.slide import Slide

priority = 1


def is_supported(filepath):
    path = pathlib.Path(filepath)
    if path.is_file():
        return False
    else:
        if path.name.endswith("ome.tif") or path.name.endswith("ome.tiff"):
            return False
        return path.suffix in [".svs", ".tiff", ".tif"]


async def open(filepath):
    return await Slide.create(filepath)
