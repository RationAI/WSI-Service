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
        return filename.endswith("ome.tif") or filename.endswith("ome.tiff")
    else:
        return False


async def open(filepath):
    return await Slide.create(filepath)
