import os
from pathlib import Path
from .local_id_creation import create_slide_object
from .extensions import Extensions


def get_extension(file_path):
    base, splitted_last = os.path.splitext(file_path)
    _, splitted_second = os.path.splitext(base)
    if splitted_second.lower() == ".ome":
        return splitted_second.lower() + splitted_last.lower()
    return splitted_last.lower()


def get_file_extensions(folder_path):
    extensions = {
        file.suffix.lower() for file in Path(folder_path).iterdir() if file.is_file()
    }
    return extensions


def control_mrxs(settings, file_path, case_id, cases, slides, controlled_path):
    filename, file_ext = os.path.splitext(file_path)
    filename = os.path.basename(filename)
    corresponding_dir = os.path.join(os.path.dirname(file_path), filename)

    controlled_path.add(file_path)

    if not os.path.isdir(corresponding_dir) or not os.path.exists(corresponding_dir):
        print(f"No corresponding directory found for the file {file_path}.")
        return controlled_path, cases

    slidedat_ini_path = os.path.join(corresponding_dir, "Slidedat.ini")

    if not os.path.exists(slidedat_ini_path):
        print(f"Slidedat.ini file is missing in the directory {corresponding_dir}.")
        return controlled_path, cases

    files = [f for f in os.listdir(corresponding_dir)]

    for f in files:
        extention = get_extension(f)
        if extention != ".dat" and extention != ".ini":
            print(f"Unsupported file format for .mrxs {f}.")
            return controlled_path, cases
    slide = create_slide_object(file_path, cases[case_id])
    cases[case_id].slides.append(slide.local_id)
    slides[slide.local_id] = slide
    return controlled_path, cases


def control_dcm(settings, file_path, case_id, cases, slides, controlled_path):
    if os.path.isdir(file_path):
        files = [f for f in os.listdir(file_path)]
    else:
        file_path = os.path.dirname(file_path)
        files = [f for f in os.listdir(file_path)]
    for f in files:
        controlled_path.add(os.path.join(file_path, f))
        if get_extension(f) != ".dcm" and f != "DICOMDIR":
            print(f"Unsupported file format for .dcm {f}.")
            return controlled_path, cases
    files = sorted(files)
    slide = files[0]
    if slide == "DICOMDIR":
        slide = files[1]
    slide = create_slide_object(os.path.join(file_path, slide), cases[case_id])
    cases[case_id].slides.append(slide.local_id)
    slides[slide.local_id] = slide
    # controlled_path.add(file_path)

    return controlled_path, cases


def control_vsf(settings, file_path, case_id, cases, slides, controlled_path):

    # .vsf
    # .img
    # .jpg

    base, _ = os.path.splitext(file_path)
    vsf = str(base) + ".vsf"
    img = str(base) + ".img"
    jpg = str(base) + ".jpg"
    if os.path.exists(vsf) and os.path.exists(jpg) and os.path.exists(img):
        slide = create_slide_object(vsf, cases[case_id])
        cases[case_id].slides.append(slide.local_id)
        slides[slide.local_id] = slide
        controlled_path.add(vsf)
        controlled_path.add(img)
        controlled_path.add(jpg)
        return controlled_path, cases

    print("Error: Folder must contain one .vsf, one .img, and one .jpg file.")
    controlled_path.add(file_path)
    return controlled_path, cases


def is_allowed_extension(extension):
    if extension in Extensions.get_allowed_extensions():
        return True
    print(f"The extention is not supported: {extension}")
    return False


def multi_extension_control(settings, file_path, case_id, cases, slides, controlled_path):
    multi_extension_control_map = {
        ".mrxs": control_mrxs,
        ".dcm": control_dcm,
        ".vsf": control_vsf,
        ".img": control_vsf,
        ".jpg": control_vsf,
    }
    _, extension = os.path.splitext(file_path)
    return multi_extension_control_map[extension](
        settings, file_path, case_id, cases, slides, controlled_path
    )
