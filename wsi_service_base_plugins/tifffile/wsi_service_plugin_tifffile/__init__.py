import pathlib

from wsi_service_plugin_tifffile.slide import Slide


def is_supported(filepath):
    path = pathlib.Path(filepath)
    if path.is_file():
        for suffix in ["ome.tif", "ome.tiff", "ome.tf2", "ome.tf8", "ome.btf"]:
            if path.name.endswith(suffix):
                return True
    return False


async def open(filepath):
    return await Slide.create(filepath)
