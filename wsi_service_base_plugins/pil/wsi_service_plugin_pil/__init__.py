from .slide import Slide

supported_file_extensions = [".png", ".jpg", ".jpeg"]


def open(filepath, slide_id=0):
    return Slide(filepath, slide_id)
