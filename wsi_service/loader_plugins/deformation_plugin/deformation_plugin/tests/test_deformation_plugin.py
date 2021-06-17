import os
import sqlite3

import numpy as np
import pytest
import requests_mock
from PIL import Image

try:
    import wsi_service.loader_plugins.deformation_plugin.deformation_plugin.tests.testdata as testdata
    from wsi_service.loader_plugins.deformation_plugin.deformation_plugin import Deformation

    def setup_mock(kwargs):
        mock = kwargs["requests_mock"]
        mock.get(
            "http://testserver_registration/v1/slides/4b0ec5e0ec5e5e05ae9e500857314f20/info",
            json={
                "id": "4b0ec5e0ec5e5e05ae9e500857314f20",
                "channels": [
                    {"id": 0, "name": "Red", "color": {"r": 255, "g": 0, "b": 0, "a": 0}},
                    {"id": 1, "name": "Green", "color": {"r": 0, "g": 255, "b": 0, "a": 0}},
                    {"id": 2, "name": "Blue", "color": {"r": 0, "g": 0, "b": 255, "a": 0}},
                ],
                "channel_depth": 8,
                "extent": {"x": 46000, "y": 32914, "z": 1},
                "num_levels": 10,
                "pixel_size_nm": {"x": 49.9001996007984, "y": 49.9001996007984, "z": None},
                "tile_extent": {"x": 128, "y": 128, "z": 1},
                "levels": [
                    {"extent": {"x": 46000, "y": 32914, "z": 1}, "downsample_factor": 1},
                    {"extent": {"x": 23000, "y": 16457, "z": 1}, "downsample_factor": 2},
                    {"extent": {"x": 11500, "y": 8228, "z": 1}, "downsample_factor": 4.000121536217793},
                    {"extent": {"x": 5750, "y": 4114, "z": 1}, "downsample_factor": 8.000243072435586},
                    {"extent": {"x": 2875, "y": 2057, "z": 1}, "downsample_factor": 16.00048614487117},
                    {"extent": {"x": 1437, "y": 1028, "z": 1}, "downsample_factor": 32.01432201760585},
                    {"extent": {"x": 718, "y": 514, "z": 1}, "downsample_factor": 64.05093591147048},
                    {"extent": {"x": 359, "y": 257, "z": 1}, "downsample_factor": 128.10187182294095},
                    {"extent": {"x": 179, "y": 128, "z": 1}, "downsample_factor": 257.06193261173183},
                    {"extent": {"x": 89, "y": 64, "z": 1}, "downsample_factor": 515.5675912921348},
                ],
            },
        )
        mock.get(
            "http://testserver_registration/v1/slides/4b0ec5e0ec5e5e05ae9e500857314f20/region/level/2/start/3050/3550/size/1000/1000?image_format=jpeg",
            content=testdata.fetch_region_3050,
            headers={"content-type": "image/jpeg", "transfer-encoding": "chunked"},
        )
        mock.get(
            "http://testserver_registration/v1/slides/4b0ec5e0ec5e5e05ae9e500857314f20/region/level/2/start/2950/3450/size/1200/1200?image_format=jpeg",
            content=testdata.fetch_region_2950,
            headers={"content-type": "image/jpeg", "transfer-encoding": "chunked"},
        )
        mock.get(
            "http://testserver_registration/v1/slides/4b0ec5e0ec5e5e05ae9e500857314f20/region/level/2/start/3000/3500/size/1200/1200?image_format=jpeg",
            content=testdata.fetch_region_3000,
            headers={"content-type": "image/jpeg", "transfer-encoding": "chunked"},
        )
        return mock

    @pytest.fixture
    def deformation_file_all_ones_or_zeroes():
        try:
            os.mkdir("test_data")
        except:
            pass
        n_pixels = 513
        deformation_zeros = np.zeros((n_pixels, n_pixels)).tobytes()
        deformation_ones = np.ones((n_pixels, n_pixels)).tobytes()
        deformation_dot_zero_ones = (0.01 * np.ones((n_pixels, n_pixels))).tobytes()

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
            (deformation_ones, deformation_ones, n_pixels, n_pixels, Wdef, slideid),
        )
        conn.commit()
        conn.close()

        filename = "test_data/zeros.sqreg"
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
            (deformation_zeros, deformation_zeros, n_pixels, n_pixels, Wdef, slideid),
        )

        conn.commit()
        conn.close()

        filename = "test_data/dot_zero_ones.sqreg"
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
            (deformation_dot_zero_ones, deformation_dot_zero_ones, n_pixels, n_pixels, Wdef, slideid),
        )

        conn.commit()
        conn.close()

    @requests_mock.Mocker(real_http=True, kw="requests_mock")
    def test_get_four_edges_world(deformation_file_all_ones_or_zeroes, **kwargs):
        setup_mock(kwargs)
        deformation_file_all_ones_or_zeroes
        d = Deformation("test_data/zeros.sqreg", wsi_service="http://testserver_registration")
        WR = np.array([[0.1, 0, 0, 10], [0, 0.1, 0, 10], [0, 0, 1, 0], [0, 0, 0, 1]])
        targetSizePixel = [512, 512]

        pts = d.get_four_edges_world(WR, targetSizePixel)

        assert (pts[0][0:2] == [10, 10]).all()
        assert (pts[2][0:2] == [10, 10 + 512 / 10]).all()
        assert (pts[1][0:2] == [10 + 512 / 10, 10]).all()
        assert (pts[3][0:2] == [10 + 512 / 10, 10 + 512 / 10]).all()

    @requests_mock.Mocker(real_http=True, kw="requests_mock")
    def test_get_target_area(**kwargs):
        setup_mock(kwargs)
        WR = np.array([[0.1, 0, 0, 10], [0, 0.1, 0, 10], [0, 0, 1, 0], [0, 0, 0, 1]])
        sourceSizePixel = [512, 512]

        d = Deformation("test_data/ones.sqreg", wsi_service="http://testserver_registration")
        # d._defInterp, filepath, filepath = d.deformation_from_file()
        WT_region, start_T_px, targetArray = d.get_target_region_area(WR, sourceSizePixel)

        assert WT_region[0, 3] == start_T_px[0] * WR[0, 0]
        assert WT_region[0, 3] < WR[0, 3]
        assert WT_region[0, 3] == pytest.approx(
            WR[0, 3] - (WR[0, 0] * sourceSizePixel[0] * 0.1) + 1, 0.1
        )  # reference region - 10% offset + 1 deformation
        assert WT_region[1, 3] == pytest.approx(WR[1, 3] - (WR[1, 1] * sourceSizePixel[1] * 0.1) + 1, 0.1)
        assert targetArray[0] > 512 * 1.2

    @requests_mock.Mocker(real_http=True, kw="requests_mock")
    def test_get_target_area_no_deformation(**kwargs):
        setup_mock(kwargs)
        WR = np.array([[0.1, 0, 0, 10], [0, 0.1, 0, 10], [0, 0, 1, 0], [0, 0, 0, 1]])
        sourceSizePixel = [512, 512]

        d = Deformation("test_data/zeros.sqreg", wsi_service="http://testserver_registration")
        WT, _start_T_px, targetSizePixel = d.get_target_region_area(WR, sourceSizePixel)

        # just extended, no deformation added
        assert WT[0, 3] == pytest.approx(
            WR[0, 3] - (WR[0, 0] * sourceSizePixel[0] * 0.1) + 0, 0.1
        )  # reference region - 10% offset + 0 deformation
        assert WT[1, 3] == pytest.approx(WR[1, 3] - (WR[1, 1] * sourceSizePixel[1] * 0.1) + 0, 0.1)
        assert 512 * 1.15 < targetSizePixel[0] < 512 * 1.25
        assert 512 * 1.15 < targetSizePixel[1] < 512 * 1.25

    @requests_mock.Mocker(real_http=True, kw="requests_mock")
    def test_get_region_no_def(**kwargs):
        setup_mock(kwargs)
        sourceSizePixel = [1000, 1000]

        d = Deformation("test_data/zeros.sqreg", wsi_service="http://testserver_registration")

        level = 2
        start_x = 3050
        start_y = 3550
        size_x = sourceSizePixel[0]
        size_y = sourceSizePixel[1]
        rgb_imageR = d.get_region(level, start_x, start_y, size_x, size_y, 0, image_format="jpeg")
        rgb_imageT = d.get_region(level, start_x, start_y, size_x, size_y, 1, image_format="jpeg")
        # rgb_imageR.show()
        # rgb_imageT.show()
        assert rgb_imageR.getpixel((0, 0)) == pytest.approx(rgb_imageT.getpixel((0, 0)), 1)
        assert rgb_imageR.getpixel((10, 10)) == pytest.approx(rgb_imageT.getpixel((0, 0)), 1)
        assert rgb_imageR.getpixel((sourceSizePixel[0] - 1, sourceSizePixel[1] - 1)) == rgb_imageT.getpixel(
            (sourceSizePixel[0] - 1, sourceSizePixel[1] - 1)
        )

    @pytest.mark.skip(reason="too complicated to mock, added simpler test below")
    def test_get_region_with_def_many(deformation_file_all_ones_or_zeroes, **kwargs):
        deformation_file_all_ones_or_zeroes
        sourceSizePixel = [300, 400]

        d = Deformation("test_data/dot_zero_ones.sqreg", wsi_service="http://localhost:8080")

        for level in [0, 2, 4, 6]:
            start_x = int(8000 / 2 ** level)
            start_y = int(16000 / 2 ** level)
            size_x = sourceSizePixel[0]
            size_y = sourceSizePixel[1]
            rgb_imageR = d.get_region(level, start_x, start_y, size_x, size_y, 0, image_format="jpeg")
            rgb_imageT = d.get_region(level, start_x, start_y, size_x, size_y, 1, image_format="jpeg")
            # rgb_imageR.show()
            # rgb_imageT.show()

            shift_in_pixels = round(0.01 / d.get_world_matrix(level, 0)[0, 0])
            assert rgb_imageR.getpixel((shift_in_pixels, shift_in_pixels)) == pytest.approx(
                rgb_imageT.getpixel((0, 0)), 3
            )
            assert rgb_imageR.getpixel((shift_in_pixels + 10, shift_in_pixels + 10)) == pytest.approx(
                rgb_imageT.getpixel((10, 10)), 3
            )
            assert rgb_imageR.getpixel((shift_in_pixels + 99, shift_in_pixels + 11)) == pytest.approx(
                rgb_imageT.getpixel((99, 11)), 3
            )

    @requests_mock.Mocker(real_http=True, kw="requests_mock")
    def test_get_region_with_def(deformation_file_all_ones_or_zeroes, **kwargs):
        setup_mock(kwargs)
        deformation_file_all_ones_or_zeroes
        sourceSizePixel = [1000, 1000]

        d = Deformation("test_data/dot_zero_ones.sqreg", wsi_service="http://testserver_registration")

        for level in [2]:
            start_x = 3050
            start_y = 3550
            size_x = sourceSizePixel[0]
            size_y = sourceSizePixel[1]
            rgb_imageR = d.get_region(level, start_x, start_y, size_x, size_y, 0, image_format="jpeg")
            rgb_imageT = d.get_region(level, start_x, start_y, size_x, size_y, 1, image_format="jpeg")
            # rgb_imageR.show()
            # rgb_imageT.show()

            shift_in_pixels = round(0.01 / d.get_world_matrix(level, 0)[0, 0])
            assert rgb_imageR.getpixel((shift_in_pixels, shift_in_pixels)) == pytest.approx(
                rgb_imageT.getpixel((0, 0)), 3
            )
            assert rgb_imageR.getpixel((shift_in_pixels + 10, shift_in_pixels + 10)) == pytest.approx(
                rgb_imageT.getpixel((10, 10)), 3
            )
            assert rgb_imageR.getpixel((shift_in_pixels + 99, shift_in_pixels + 11)) == pytest.approx(
                rgb_imageT.getpixel((99, 11)), 3
            )

    @requests_mock.Mocker(real_http=True, kw="requests_mock")
    def test_get_fetch_image(**kwargs):
        setup_mock(kwargs)
        sourceSizePixel = (1000, 1000)

        d = Deformation("test_data/zeros.sqreg", wsi_service="http://testserver_registration")

        level = 2
        start_x = 3050
        start_y = 3550
        size_x = sourceSizePixel[0]
        size_y = sourceSizePixel[1]
        z = 0
        rgb_image = d.fetch_region(level, start_x, start_y, size_x, size_y, z)
        assert rgb_image.size == sourceSizePixel

    @requests_mock.Mocker(real_http=True, kw="requests_mock")
    def test_get_world_matrix(**kwargs):
        setup_mock(kwargs)
        d = Deformation("test_data/zeros.sqreg", wsi_service="http://testserver_registration")
        level = 0
        z = 0
        W = d.get_world_matrix(level, z)
        assert W[0, 0] == 49.9001996007984 / 1e6
        level = 2
        W = d.get_world_matrix(level, z)
        assert W[0, 0] == pytest.approx(49.9001996007984 / 1e6 * 2 * 2, 1e-4)


except (ModuleNotFoundError, ImportError):
    print("Deformation module could not be loaded. Aborting tests.")

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
