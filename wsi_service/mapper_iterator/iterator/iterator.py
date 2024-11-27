import os
from pathlib import Path
from .control_extensions import (
    control_mrxs,
    get_extension,
    multi_extension_control,
    is_allowed_extension,
    control_dcm,
    get_file_extensions,
)
from .local_id_creation import create_case_object
from .extensions import Extensions
from .local_id_creation import create_slide_object


def control_dir(settings, file_path, case_id, cases, slides, controlled_path):

    mrxs = str(file_path) + ".mrxs"
    if os.path.exists(mrxs) and mrxs not in controlled_path:
        return control_mrxs(
            settings, str(file_path) + ".mrxs", case_id, cases, slides, controlled_path
        )
    if ".dcm" in get_file_extensions(file_path):
        return control_dcm(settings, file_path, case_id, cases, slides, controlled_path)
    return control_files(settings, file_path, cases, slides, controlled_path)


def control_files(settings, source_path, cases, slides, controlled_path):

    case = create_case_object(settings, source_path)
    cases.update({case.local_id: case})

    files = [f for f in os.listdir(source_path)]
    for file in files:

        file_path = os.path.join(source_path, file)
        extension = get_extension(file_path)
        if os.path.isdir(file_path):
            controlled_path, cases = control_dir(
                settings, file_path, case.local_id, cases, slides, controlled_path
            )
        elif file_path not in controlled_path and is_allowed_extension(extension):
            if extension not in Extensions.get_multi_extensions():
                slide = create_slide_object(file_path, cases[case.local_id])
                cases[case.local_id].slides.append(slide.local_id)
                slides[slide.local_id] = slide
                controlled_path.add(file_path)
            else:
                controlled_path, cases = multi_extension_control(
                    settings, file_path, case.local_id, cases, slides, controlled_path
                )
    return controlled_path, cases


def iterate(settings):
    cases = dict()
    slides = dict()
    controlled_path = set()
    source_path = Path(settings.source_path).expanduser()

    if not os.path.exists(source_path):
        print(f"Path does not exist: {source_path}")
        return cases
    if not os.path.isdir(source_path):
        source_path = os.path.dirname(source_path)
    controlled_path, cases = control_files(
        settings, source_path, cases, slides, controlled_path
    )
    return cases, slides
