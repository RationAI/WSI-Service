import os
import pathlib

from wsi_service_plugin_tifffile.slide import Slide

supported_file_extensions = [
    ".ome.tif",
    ".ome.tiff",
    ".tf2",
    ".tf8",
    ".btf",
]


def is_supported(filepath):
    if os.path.isfile(filepath):
        filename = pathlib.Path(filepath).name
        for suffix in ["ome.tif", "ome.tiff", "ome.tf2", "ome.tf8", "ome.btf"]:
            if filename.endswith(suffix):
                return True
    return False


async def open(filepath):
    return await Slide.create(filepath)
