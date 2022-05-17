from wsi_service_plugin_wsidicom.slide import Slide

supported_file_extensions = ["dicom-folder"]


async def open(filepath):
    return await Slide.create(filepath)
