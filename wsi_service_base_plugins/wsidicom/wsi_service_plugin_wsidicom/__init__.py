import glob
import os

from wsi_service_plugin_wsidicom.slide import Slide


def is_supported(filepath):
    return len(glob.glob(os.path.join(filepath, "*.dcm"))) > 0


async def open(filepath):
    return await Slide.create(filepath)
