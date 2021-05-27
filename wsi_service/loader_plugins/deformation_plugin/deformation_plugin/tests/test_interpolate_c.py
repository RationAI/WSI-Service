import numpy as np
import pytest

try:
    from _interpolate import ffi
    from _interpolate.lib import interpolate_tile

    @pytest.fixture
    def data():
        in_start_px_x = 100  # offset of template image tile in pixels
        in_start_px_y = 100
        out_start_px_x = 200  # offset of reference image tile in pixels
        out_start_px_y = 200
        channels = 3
        in_size_x = 1000
        in_size_y = 800
        out_size_x = 800
        out_size_y = 600
        undeformedT = ffi.new("double[]", in_size_x * in_size_y * channels)  # in_image

        for i in range(in_size_x * in_size_y * channels):
            undeformedT[i] = i
        deformedT = ffi.new("double[]", out_size_x * out_size_y * channels)

        WR = ffi.new("double[]", 16)
        WR[0:16] = np.eye(4, dtype=np.float64).flatten()[0:16]

        WTInv = ffi.new("double[]", 16)
        WTInv[0:16] = np.eye(4, dtype=np.float64).flatten()[0:16]

        Wdef = ffi.new("double[]", 16)
        Wdef[0:16] = np.eye(4, dtype=np.float64).flatten()[0:16]
        Wdef[0] = 10
        Wdef[5] = 10
        Wdef[3] = -Wdef[0] / 2
        Wdef[7] = -Wdef[5] / 2

        Wdef_inv = ffi.new("double[]", 16)
        Wdef_inv[0:16] = np.eye(4, dtype=np.float64).flatten()[0:16]
        Wdef_inv[0] = 0.1
        Wdef_inv[5] = 0.1
        Wdef_inv[3] = 0.5
        Wdef_inv[7] = 0.5

        size_def_x = 257
        size_def_y = 257
        deformation_x = ffi.new("double[]", size_def_x * size_def_y)
        deformation_y = ffi.new("double[]", size_def_x * size_def_y)

        return (
            undeformedT,
            deformedT,
            in_size_x,
            in_size_y,
            out_size_x,
            out_size_y,
            channels,
            in_start_px_x,
            in_start_px_y,
            out_start_px_x,
            out_start_px_y,
            WR,
            WTInv,
            deformation_x,
            deformation_y,
            Wdef,
            Wdef_inv,
            size_def_x,
            size_def_y,
        )

    def test_interpolate_nodef(data):
        (
            undeformedT,
            deformedT,
            in_size_x,
            in_size_y,
            out_size_x,
            out_size_y,
            channels,
            in_start_px_x,
            in_start_px_y,
            out_start_px_x,
            out_start_px_y,
            WR,
            WTInv,
            deformation_x,
            deformation_y,
            Wdef,
            Wdef_inv,
            size_def_x,
            size_def_y,
        ) = data
        # WR and WT are relative to the full template/reference image
        interpolate_tile(
            undeformedT,
            deformedT,
            in_size_x,
            in_size_y,
            out_size_x,
            out_size_y,
            channels,
            in_start_px_x,
            in_start_px_y,
            out_start_px_x,
            out_start_px_y,
            WR,
            WTInv,
            deformation_x,
            deformation_y,
            Wdef,
            Wdef_inv,
            size_def_x,
            size_def_y,
        )

        for x in range(out_size_x):
            for y in range(out_size_y):
                # print("out({}, {}) = {}, in({},{}) = {}".format(x,y,deformedT[x + out_size_x * y],
                #     (out_start_px_x - in_start_px_x) + x, (out_start_px_y - in_start_px_y + y) ,
                #     undeformedT[(out_start_px_x - in_start_px_x) + x + in_size_x * (out_start_px_y - in_start_px_y + y)]) )
                assert (
                    deformedT[x + out_size_x * y]
                    == undeformedT[
                        (out_start_px_x - in_start_px_x) + x + in_size_x * (out_start_px_y - in_start_px_y + y)
                    ]
                )

    def test_interpolate_static_def(data):
        (
            undeformedT,
            deformedT,
            in_size_x,
            in_size_y,
            out_size_x,
            out_size_y,
            channels,
            in_start_px_x,
            in_start_px_y,
            out_start_px_x,
            out_start_px_y,
            WR,
            WTInv,
            deformation_x,
            deformation_y,
            Wdef,
            Wdef_inv,
            size_def_x,
            size_def_y,
        ) = data
        d_x = 1.0
        d_y = 1.0
        for i in range(size_def_x * size_def_y):
            deformation_x[i] = d_x
            deformation_y[i] = d_y

        interpolate_tile(
            undeformedT,
            deformedT,
            in_size_x,
            in_size_y,
            out_size_x,
            out_size_y,
            channels,
            in_start_px_x,
            in_start_px_y,
            out_start_px_x,
            out_start_px_y,
            WR,
            WTInv,
            deformation_x,
            deformation_y,
            Wdef,
            Wdef_inv,
            size_def_x,
            size_def_y,
        )

        for x in range(out_size_x):
            for y in range(out_size_y):
                # print("out({}, {}) = {}, in({},{}) = {}".format(x, y, deformedT[x + out_size_x * y],
                #     (out_start_px_x - in_start_px_x) + x, (out_start_px_y - in_start_px_y + y) ,
                #     undeformedT[(out_start_px_x - in_start_px_x) + x + int(Wdef[0] * d_x) + in_size_x * (out_start_px_y - in_start_px_y + (y + int(Wdef[5] * d_y)))]))
                assert (
                    deformedT[x + out_size_x * y]
                    == undeformedT[
                        (out_start_px_x - in_start_px_x)
                        + x
                        + int(d_x)
                        + in_size_x * (out_start_px_y - in_start_px_y + (y + int(d_y)))
                    ]
                )


except (ModuleNotFoundError, ImportError):
    print("Deformation module could not be loaded. Aborting tests.")
