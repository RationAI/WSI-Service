import glob
import os
import pathlib

from wsi_service_plugin_wsidicom.slide import Slide


def is_supported(filepath):
    if os.path.isfile(filepath):
        return False
    else:
        return any(filename.endswith(".dcm") for filename in pathlib.Path(filepath).iterdir())


async def open(filepath):
    return await Slide.create(filepath)
