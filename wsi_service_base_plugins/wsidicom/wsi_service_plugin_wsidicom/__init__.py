import pathlib

from wsi_service_plugin_wsidicom.slide import Slide


def is_supported(filepath):
    path = pathlib.Path(filepath)
    if path.is_dir():
        return False
    else:
        return any(list(path.glob("*.dcm")))


async def open(filepath):
    return await Slide.create(filepath)
