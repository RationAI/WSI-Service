import os
import sqlite3

import numpy as np
import pytest
import requests_mock
from PIL import Image

from wsi_service.loader_plugins.deformation_plugin.deformation_plugin import Deformation


@pytest.fixture
def deformation_file_all_ones_or_zeroes():
    n_pixels = 513
    deformation_zeros = np.zeros((n_pixels, n_pixels)).tobytes()
    deformation_ones = np.ones((n_pixels, n_pixels)).tobytes()

    Wdef = np.eye(4)
    Wdef[0, 0] = 10
    Wdef[1, 1] = 10
    Wdef[0, 3] = -5
    Wdef[1, 3] = -5
    Wdef = Wdef.tobytes()

    filename = "test_data/ones.sqreg"
    try:
        os.remove(filename)
    except:
        pass
    conn = sqlite3.connect(filename)
    c = conn.cursor()
    slideid = "4b0ec5e0ec5e5e05ae9e500857314f20"

    c.execute(
        "CREATE TABLE sqreg (Slice Int , ImageFileName String, defX BLOB, defY BLOB, shapeX Int, shapeY Int, W BLOB, GlobalSlideID String, PRIMARY KEY (Slice))"
    )
    c.execute("INSERT INTO sqreg VALUES(0,'_',NULL,NULL,0,0,NULL, ?)", (slideid,))
    c.execute(
        "INSERT INTO sqreg VALUES(1,'_',?,?,?,?,?, ?)",
        (
            deformation_ones,
            deformation_ones,
            n_pixels,
            n_pixels,
            Wdef,
            slideid,
        ),
    )
    conn.commit()
    conn.close()

    filename = "zeros.sqreg"
    try:
        os.remove(filename)
    except:
        pass
    conn = sqlite3.connect(filename)
    c = conn.cursor()
    slideid = "4b0ec5e0ec5e5e05ae9e500857314f20"

    c.execute(
        "CREATE TABLE sqreg (Slice Int , ImageFileName String, defX BLOB, defY BLOB, shapeX Int, shapeY Int, W BLOB, GlobalSlideID String, PRIMARY KEY (Slice))"
    )
    c.execute("INSERT INTO sqreg VALUES(0,'_',NULL,NULL,0,0,NULL, ?)", (slideid,))
    c.execute(
        "INSERT INTO sqreg VALUES(1,'_',?,?,?,?,?, ?)",
        (
            deformation_zeros,
            deformation_zeros,
            n_pixels,
            n_pixels,
            Wdef,
            slideid,
        ),
    )

    conn.commit()
    conn.close()


def test_get_four_edges_world(deformation_file_all_ones_or_zeroes):
    deformation_file_all_ones_or_zeroes
    d = Deformation("test_data/zeros.sqreg")
    WR = np.array([[0.1, 0, 0, 10], [0, 0.1, 0, 10], [0, 0, 1, 0], [0, 0, 0, 1]])
    targetSizePixel = [512, 512]

    pts = d.get_four_edges_world(WR, targetSizePixel)

    assert (pts[0][0:2] == [10, 10]).all()
    assert (pts[2][0:2] == [10, 10 + 512 / 10]).all()
    assert (pts[1][0:2] == [10 + 512 / 10, 10]).all()
    assert (pts[3][0:2] == [10 + 512 / 10, 10 + 512 / 10]).all()


def test_get_target_area():
    WR = np.array([[0.1, 0, 0, 10], [0, 0.1, 0, 10], [0, 0, 1, 0], [0, 0, 0, 1]])
    sourceSizePixel = [512, 512]

    d = Deformation("test_data/ones.sqreg")
    # d._defInterp, filepath, filepath = d.deformation_from_file()
    WT_region, start_T_px, targetArray = d.get_target_region_area(WR, sourceSizePixel)

    assert WT_region[0, 3] == start_T_px[0] * WR[0, 0]
    assert WT_region[0, 3] < WR[0, 3]
    assert WT_region[0, 3] == pytest.approx(
        WR[0, 3] - (WR[0, 0] * sourceSizePixel[0] * 0.1) + 1, 0.1
    )  # reference region - 10% offset + 1 deformation
    assert WT_region[1, 3] == pytest.approx(WR[1, 3] - (WR[1, 1] * sourceSizePixel[1] * 0.1) + 1, 0.1)
    assert targetArray[0] > 512 * 1.2


def test_get_target_area_no_deformation():
    WR = np.array([[0.1, 0, 0, 10], [0, 0.1, 0, 10], [0, 0, 1, 0], [0, 0, 0, 1]])
    sourceSizePixel = [512, 512]

    d = Deformation("test_data/zeros.sqreg")
    WT, _start_T_px, targetSizePixel = d.get_target_region_area(WR, sourceSizePixel)

    # just extended, no deformation added
    assert WT[0, 3] == pytest.approx(
        WR[0, 3] - (WR[0, 0] * sourceSizePixel[0] * 0.1) + 0, 0.1
    )  # reference region - 10% offset + 0 deformation
    assert WT[1, 3] == pytest.approx(WR[1, 3] - (WR[1, 1] * sourceSizePixel[1] * 0.1) + 0, 0.1)
    assert 512 * 1.15 < targetSizePixel[0] < 512 * 1.25
    assert 512 * 1.15 < targetSizePixel[1] < 512 * 1.25


def test_get_region_no_def():
    sourceSizePixel = [1000, 1000]

    d = Deformation("test_data/zeros.sqreg", wsi_service="http://localhost:8080")

    level = 2
    start_x = 3050
    start_y = 3550
    size_x = sourceSizePixel[0]
    size_y = sourceSizePixel[1]
    rgb_imageR = d.get_region(level, start_x, start_y, size_x, size_y, 0, image_format="png")
    rgb_imageT = d.get_region(level, start_x, start_y, size_x, size_y, 1, image_format="png")
    # rgb_imageR.show()
    # rgb_imageT.show()
    assert rgb_imageR.getpixel((0, 0)) == pytest.approx(rgb_imageT.getpixel((0, 0)), 1)
    assert rgb_imageR.getpixel((10, 10)) == pytest.approx(rgb_imageT.getpixel((0, 0)), 1)
    assert rgb_imageR.getpixel((sourceSizePixel[0] - 1, sourceSizePixel[1] - 1)) == rgb_imageT.getpixel(
        (sourceSizePixel[0] - 1, sourceSizePixel[1] - 1)
    )


# @pytest.mark.skip(reason="does not work yet")
def test_get_region_with_def(deformation_file_all_ones_or_zeroes):
    deformation_file_all_ones_or_zeroes
    sourceSizePixel = [300, 400]

    d = Deformation("test_data/dot_zero_ones.sqreg", wsi_service="http://localhost:8080")

    for level in [0, 2, 4, 6]:
        start_x = int(8000 / 2 ** level)
        start_y = int(16000 / 2 ** level)
        size_x = sourceSizePixel[0]
        size_y = sourceSizePixel[1]
        rgb_imageR = d.get_region(level, start_x, start_y, size_x, size_y, 0, image_format="png")
        rgb_imageT = d.get_region(level, start_x, start_y, size_x, size_y, 1, image_format="png")
        # rgb_imageR.show()
        # rgb_imageT.show()

        shift_in_pixels = round(0.01 / d.get_world_matrix(level, 0)[0, 0])
        assert rgb_imageR.getpixel((shift_in_pixels, shift_in_pixels)) == pytest.approx(rgb_imageT.getpixel((0, 0)), 3)
        assert rgb_imageR.getpixel((shift_in_pixels + 10, shift_in_pixels + 10)) == pytest.approx(
            rgb_imageT.getpixel((10, 10)), 3
        )
        assert rgb_imageR.getpixel((shift_in_pixels + 99, shift_in_pixels + 11)) == pytest.approx(
            rgb_imageT.getpixel((99, 11)), 3
        )


def test_get_fetch_image():
    WR = np.array([[0.1, 0, 0, 10], [0, 0.1, 0, 10], [0, 0, 1, 0], [0, 0, 0, 1]])
    sourceSizePixel = (512, 512)

    d = Deformation("test_data/zeros.sqreg", wsi_service="http://localhost:8080")

    level = 0
    start_x = int(WR[0, 3] / WR[0, 0])
    start_y = int(WR[1, 3] / WR[1, 1])
    size_x = sourceSizePixel[0]
    size_y = sourceSizePixel[1]
    z = 0
    rgb_image = d.fetch_region(level, start_x, start_y, size_x, size_y, z)
    assert rgb_image.size == sourceSizePixel


def test_get_world_matrix():
    d = Deformation("test_data/zeros.sqreg")
    level = 0
    z = 0
    W = d.get_world_matrix(level, z)
    assert W[0, 0] == 49.9001996007984 / 1e6
    level = 2
    W = d.get_world_matrix(level, z)
    assert W[0, 0] == pytest.approx(49.9001996007984 / 1e6 * 2 * 2, 1e-4)


## Helpers


def deformation_from_file_no_interp_dummy_one(self):
    dims = 512
    defX = np.ones((dims, dims))
    defY = np.ones((dims, dims))
    Wdef = np.eye(4)
    Wdef[0, 0] = 0.5
    Wdef[1, 1] = 0.5

    return (defX, defY, Wdef, dims, "", "")


def deformation_from_file_no_interp_dummy_zero(self):
    dims = 512
    defX = np.zeros((dims, dims))
    defY = np.zeros((dims, dims))
    Wdef = np.eye(4)
    Wdef[0, 0] = 0.5
    Wdef[1, 1] = 0.5

    return (defX, defY, Wdef, dims, "", "")
