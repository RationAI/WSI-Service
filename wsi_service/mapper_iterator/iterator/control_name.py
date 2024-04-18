import os


def get_filename(filename_path):
    extensions = {
        ".tf2",
        ".tf8",
        ".tif",
        ".tiff",
    }
    tail = os.path.basename(filename_path)
    base, ext = os.path.splitext(tail)
    if ext in extensions:
        base02, ext02 = os.path.splitext(base)
        if ext02 == ".ome":
            base = base02
    return base


def control_filename(settings, path):
    base = get_filename(path)
    filename_split = base.split(".")
    if len(filename_split) != 3:
        print(f"Filename {path} does not match the pattern.")
        return False
    return True
