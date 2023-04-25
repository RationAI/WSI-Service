from wsi_service_plugin_tifffile.slide import Slide

supported_file_extensions = [
    ".ome.tif",
    ".ome.tiff",
    ".ome.tf2",
    ".ome.tf8",
    ".btf",
]


async def open(filepath):
    return await Slide.create(filepath)
