import os
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from wsi_service import Slide
from wsi_service.plugins import load_slide


def test_sync_slide_access():
    slide_path = os.path.join(get_data_path(), "testcase/CMU-1-small.tiff")
    # default plugin
    slide = Slide(slide_path)
    info_default = slide.get_info()
    max_x = 512
    max_y = 512
    thumbnail = slide.get_thumbnail(max_x, max_y)
    assert isinstance(thumbnail, np.ndarray)
    assert isinstance(Image.fromarray(thumbnail), Image.Image)
    with pytest.raises(Exception):
        slide.get_label()
    with pytest.raises(Exception):
        slide.get_macro()
    level = 0
    start_x = 0
    start_y = 0
    size_x = 256
    size_y = 256
    region = slide.get_region(level, start_x, start_y, size_x, size_y)
    assert isinstance(region, np.ndarray)
    assert isinstance(Image.fromarray(region), Image.Image)
    level = 0
    tile_x = 0
    tile_y = 0
    tile = slide.get_tile(level, tile_x, tile_y)
    assert isinstance(tile, np.ndarray)
    assert isinstance(Image.fromarray(tile), Image.Image)
    region_numpy = region.astype(np.float64)
    tile_numpy = tile.astype(np.float64)
    diff = np.abs(region_numpy - tile_numpy)
    assert np.sum(diff) == 0.0
    # specific plugin
    slide = Slide(slide_path, plugin="openslide")
    info_openslide = slide.get_info()
    assert info_default == info_openslide


def get_data_path():
    file_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(file_dir, "data")


@pytest.mark.asyncio
async def test_async_slide_access():
    slide_path = os.path.join(get_data_path(), "testcase/CMU-1-small.tiff")
    # default plugin
    slide = await load_slide(slide_path)
    info_default = await slide.get_info()
    max_x = 512
    max_y = 512
    thumbnail = await slide.get_thumbnail(max_x, max_y)
    assert isinstance(thumbnail, Image.Image)
    with pytest.raises(Exception):
        await slide.get_label()
    with pytest.raises(Exception):
        await slide.get_macro()
    level = 0
    start_x = 0
    start_y = 0
    size_x = 256
    size_y = 256
    region = await slide.get_region(level, start_x, start_y, size_x, size_y)
    assert isinstance(region, Image.Image)
    level = 0
    tile_x = 0
    tile_y = 0
    tile_bytes = await slide.get_tile(level, tile_x, tile_y)
    tile = Image.open(BytesIO(tile_bytes))
    assert isinstance(tile, Image.Image)
    region_numpy = np.array(region).astype(np.float64)
    tile_numpy = np.array(tile).astype(np.float64)
    diff = np.abs(region_numpy[tile_numpy > 0] - tile_numpy[tile_numpy > 0])
    assert np.sum(diff) == 0.0
    # specific plugin
    slide = await load_slide(slide_path, plugin="openslide")
    info_openslide = await slide.get_info()
    assert info_default == info_openslide
