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


async def open(filepath, slide_id=0):
    return Slide(filepath, slide_id)
