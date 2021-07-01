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


def open(filepath, slide_id=0):
    return Slide(filepath, slide_id)
