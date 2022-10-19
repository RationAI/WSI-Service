import glob
import os


def get_zipfly_paths(filenames):
    paths = []
    parent_folder = get_parent_folder(filenames)
    for filename in filenames:
        paths.append({"fs": filename, "n": filename.replace(parent_folder, "")})
    return paths


def get_parent_folder(filenames):
    parent_path = os.path.dirname(filenames[0])
    while any([(parent_path not in os.path.dirname(filename)) for filename in filenames]):
        parent_path = os.path.dirname(parent_path)
    return parent_path + "/"


def expand_folders(paths):
    for path in paths:
        if os.path.isdir(path):
            paths += glob.glob(os.path.join(path, "*"))
    return list(set(paths))


def remove_folders(paths):
    return [p for p in paths if not os.path.isdir(p)]
