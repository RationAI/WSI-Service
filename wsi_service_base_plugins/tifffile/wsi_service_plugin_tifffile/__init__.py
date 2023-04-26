from wsi_service_plugin_tifffile.slide import Slide

supported_file_extensions = [
    ".ome.tif",
    ".ome.tiff",
    ".tf2",
    ".tf8",
    ".btf",
]


async def open(filepath):
    return await Slide.create(filepath)
