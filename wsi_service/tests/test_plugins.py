import os
import pathlib

import pytest

from wsi_service.loader_plugins.slide_dummy import DummySlide
from wsi_service.loader_plugins.slide_openslide import OpenSlideSlide
from wsi_service.plugin_loader import load_slide, plugin_directory
from wsi_service.tests.test_api_helpers import setup_environment_variables

plugin_directory = {
    ".tiff": DummySlide,
    ".mrxs": DummySlide,
    ".svs": OpenSlideSlide,
    ".ndpi": OpenSlideSlide,
}


@pytest.mark.parametrize(
    "filepath, slide_id,",
    [
        ("tests/data/OpenSlideAdapted/Generic TIFF/CMU-1.tiff", "4b0ec5e0ec5e5e05ae9e500857314f20"),  # tiff
        ("MIRAX/Mirax2.2-1.mrxs", "7304006194f8530b9e19df1310a3670f"),  # mrxs
    ],
)
def test_check_plugins_loaded_dummy(filepath, slide_id):
    setup_environment_variables()
    filepath = os.path.join(os.environ["data_dir"], filepath)
    slide = load_slide(filepath, slide_id, plugin_directory=plugin_directory)
    assert slide.loader_name == "DummySlide"


@pytest.mark.parametrize(
    "filepath, slide_id,",
    [
        ("Aperio/CMU-1.svs", "f863c2ef155654b1af0387acc7ebdb60"),  # svs
        ("Hamamatsu/OS-1.ndpi", "c801ce3d1de45f2996e6a07b2d449bca"),  # ndpi
    ],
)
def test_check_plugins_loaded_openslide(filepath, slide_id):
    setup_environment_variables()
    filepath = os.path.join(os.environ["data_dir"], filepath)
    slide = load_slide(filepath, slide_id, plugin_directory=plugin_directory)
    assert slide.loader_name == "OpenSlide"
