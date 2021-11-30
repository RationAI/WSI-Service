from .slide import Slide

supported_file_extensions = [
    ".tif",
    ".tiff",
    ".ome.tif",
    ".ome.tiff",
    ".ome.tf2",
    ".ome.tf8",
    ".ome.btf",
]


async def open(filepath):
    return await Slide.create(filepath)
