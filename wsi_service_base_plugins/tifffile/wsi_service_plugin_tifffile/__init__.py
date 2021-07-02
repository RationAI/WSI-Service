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


def open(filepath, slide_id=0):
    return Slide(filepath, slide_id)
