import os
import pathlib

from wsi_service_plugin_wsidicom.slide import Slide


def is_supported(filepath):
    return False # todo disabled to test bioformats
    # if os.path.isfile(filepath):
    #     return False
    # else:
    #     return any(list(pathlib.Path(filepath).glob("*.dcm")))


async def open(filepath):
    return await Slide.create(filepath)
