from wsi_service_plugin_openslide.slide import Slide

supported_file_extensions = [
    ".bif",
    ".mrxs",
    ".ndpi",
    ".scn",
    ".svs",
    ".tiff",
    ".tif",
    ".vsf",
    "vsf-folder",
]


async def open(filepath):
    return await Slide.create(filepath)
