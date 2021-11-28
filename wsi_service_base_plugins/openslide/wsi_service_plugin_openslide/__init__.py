from .slide import Slide

supported_file_extensions = [
    ".bif",
    ".mrxs",
    ".ndpi",
    ".scn",
    ".svs",
    ".tiff",
    ".tif",
]


async def open(filepath):
    return await Slide.create(filepath)
