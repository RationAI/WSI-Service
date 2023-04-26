import pathlib

from wsi_service_plugin_openslide.slide import Slide


def is_supported(filepath):
    path = pathlib.Path(filepath)
    if path.is_file():
        if path.name.endswith("ome.tif") or path.name.endswith("ome.tiff"):
            return False
        return path.suffix in [".bif", ".mrxs", ".ndpi", ".scn", ".svs", ".tiff", ".tif"]
    else:
        return any(list(path.glob("*.vsf")))


async def open(filepath):
    return await Slide.create(filepath)
