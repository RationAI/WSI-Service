import os
import pathlib

import pytest
from fastapi import HTTPException

from wsi_service.loader_plugins.slide_dummy import DummySlide
from wsi_service.loader_plugins.slide_isyntax import IsyntaxSlide
from wsi_service.loader_plugins.slide_ometif import OmeTiffSlide
from wsi_service.loader_plugins.slide_openslide import OpenSlideSlide
from wsi_service.plugin_loader import load_slide, plugin_directory
from wsi_service.singletons import settings
from wsi_service.tests.api.test_api_helpers import initialize_settings

plugin_directory = {
    ".ome.tif": OmeTiffSlide,
    ".ome.tiff": OmeTiffSlide,
    ".tiff": DummySlide,
    ".mrxs": DummySlide,
    ".svs": OpenSlideSlide,
    ".ndpi": OpenSlideSlide,
    ".isyntax": IsyntaxSlide,
}


@pytest.mark.parametrize(
    "filepath, slide_id,",
    [
        ("tests/data/OpenSlideAdapted/Generic TIFF/CMU-1.tiff", "4b0ec5e0ec5e5e05ae9e500857314f20"),  # tiff
        ("OpenSlide_adapted/MIRAX/Mirax2.2-1.mrxs", "7304006194f8530b9e19df1310a3670f"),  # mrxs
    ],
)
def test_check_plugins_loaded_dummy(filepath, slide_id):
    initialize_settings()
    filepath = os.path.join(settings.data_dir, filepath)
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
    filepath = os.path.join(settings.data_dir, filepath)
    slide = load_slide(filepath, slide_id, plugin_directory=plugin_directory)
    assert slide.loader_name == "OpenSlide"


@pytest.mark.parametrize(
    "filepath, slide_id,",
    [
        ("Fluorescence OME-Tif/2019_10_15__0014_GOOD.ome.tif", "46061cfc30a65acab7a1ed644771a340"),
        ("Fluorescence OME-Tif/LuCa-7color_Scan1.ome.tiff", "56ed11a2a9e95f87a1e466cf720ceffa"),
    ],
)
def test_check_plugins_loaded_ometiff(filepath, slide_id):
    filepath = os.path.join(settings.data_dir, filepath)
    slide = load_slide(filepath, slide_id, plugin_directory=plugin_directory)
    assert slide.loader_name == "OmeTiffSlide"
