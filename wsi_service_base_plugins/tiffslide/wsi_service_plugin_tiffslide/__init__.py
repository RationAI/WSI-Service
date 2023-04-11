from wsi_service_plugin_tiffslide.slide import Slide

priority = 1

supported_file_extensions = [".svs", ".tiff", ".tif"]


async def open(filepath):
    return await Slide.create(filepath)
