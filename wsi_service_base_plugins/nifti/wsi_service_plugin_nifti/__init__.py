from pathlib import Path

from wsi_service_plugin_nifti.slide import Slide


def is_supported(filepath):
    path = Path(filepath)
    return path.is_file() and path.name.lower().endswith((".nii", ".nii.gz"))


async def open(filepath):
    return await Slide.create(filepath)
