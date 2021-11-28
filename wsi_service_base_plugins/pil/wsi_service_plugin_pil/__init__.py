from .slide import Slide

supported_file_extensions = [".png", ".jpg", ".jpeg"]


async def open(filepath):
    return await Slide.create(filepath)
