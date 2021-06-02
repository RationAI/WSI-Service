import io
import os
import sqlite3

import numpy as np
import requests
import scipy.interpolate
from PIL import Image

from ._interpolate import ffi, lib  # pylint: disable=no-name-in-module


class Deformation:
    def __init__(self, filepath: str, wsi_service: str = "http://localhost:8080"):
        self._reference_slide_index: int = 0  # TODO: find in sqreg file
        self._filepath: str = filepath
        self._wsi_service: str = wsi_service
        self._defInterp, slide_id_R, slide_id_T = self.deformation_from_file()
        self._slides = {0: slide_id_R, 1: slide_id_T}  # TODO: multiple slides?

        self.load_metadata()
        self._deformation_tuple = self.deformation_from_file_no_interp()

    def deformation_from_file_no_interp(self):
        if not os.path.isfile(self._filepath):
            raise FileNotFoundError("Deformation file does not exist: {}".format(self._filepath))
        conn = sqlite3.connect(self._filepath)
        c = conn.cursor()
        c.execute("SELECT * FROM sqreg")
        r = c.fetchone()  # TODO: this only works for z=0 as reference slide
        try:
            slide_id_R = r[7]
        except IndexError:
            print("Deformation file does not contain global slide id which is required.")
            raise
        r = c.fetchone()
        try:
            slide_id_T = r[7]
        except IndexError:
            print("Deformation file does not contain global slide id which is required.")
            raise
        dimsX = r[4]
        dimsY = r[5]
        defX = np.reshape(np.frombuffer(r[2]), (dimsX, dimsY)).T
        defY = np.reshape(np.frombuffer(r[3]), (dimsX, dimsY)).T
        Wdef = np.frombuffer(r[6])
        Wdef = np.reshape(Wdef, (4, 4))
        conn.close()
        return (np.array(defX), np.array(defY), np.array(Wdef), dimsX, dimsY, slide_id_R, slide_id_T)

    def deformation_from_file(self):
        defX, defY, Wdef, dimsX, dimsY, slide_id_R, slide_id_T = self.deformation_from_file_no_interp()
        gridX = np.arange(0, Wdef[0, 0] * dimsX, Wdef[0, 0])
        gridY = np.arange(0, Wdef[1, 1] * dimsY, Wdef[1, 1])
        defXInterp = scipy.interpolate.RectBivariateSpline(gridX, gridY, defX)
        defYInterp = scipy.interpolate.RectBivariateSpline(gridX, gridY, defY)
        return (defXInterp, defYInterp), slide_id_R, slide_id_T

    def get_target_region_area(self, WR: np.array, sourceSizePixel):
        """
        Args:
            WR (4x4 numpy float): world matrix of the source area
            sourceSizePixel ([int, int]): number of pixels of the source image

        Returns:
            4x4 numpy: world matrix of the target area
            [int, int]: number of pixels in the target image
        """
        pts = self.get_four_edges_world(WR, sourceSizePixel)
        _ptsDef, ptsDefW = self.transform_point(self._defInterp, WR, pts)

        minx = min([p[0] for p in ptsDefW])
        miny = min([p[1] for p in ptsDefW])
        maxx = max([p[0] for p in ptsDefW]) + WR[0, 0]  # end of pixel
        maxy = max([p[1] for p in ptsDefW]) + WR[1, 1]
        WT = WR.copy()

        start_x_world = minx - 0.1 * (maxx - minx)
        start_y_world = miny - 0.1 * (maxy - miny)
        # start_x_world = minx - 0.0 * (maxx - minx)
        # start_y_world = miny - 0.0 * (maxy - miny)

        start_x_px = int(round(start_x_world / WT[0, 0]))
        start_y_px = int(round(start_y_world / WT[1, 1]))

        WT[0, 3] = start_x_px * WT[0, 0]
        WT[1, 3] = start_y_px * WT[1, 1]

        extentWorld = [1.2 * (maxx - minx), 1.2 * (maxy - miny)]
        # extentWorld = [1.0 * (maxx - minx), 1.0 * (maxy - miny)]
        targetSizePixel = np.array([round(extentWorld[0] / WR[0, 0]) - 1, round(extentWorld[1] / WR[1, 1]) - 1]).astype(
            int
        )

        return WT, (start_x_px, start_y_px), targetSizePixel

    def fetch_region(
        self, level: int, start_x: int, start_y: int, size_x: int, size_y: int, z: int, image_format: str = "png"
    ) -> Image:
        slide_id = self._slides[z]
        r = requests.get(
            self._wsi_service
            + f"/v1/slides/{slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}?image_format={image_format}",
        )
        assert r.status_code == 200
        image_bytes = io.BytesIO(r.content)
        img_rgb = Image.open(image_bytes)
        img_rgb.load()
        return img_rgb

    def get_world_matrix(self, level: int, z: int):
        m = self._pixelsize_nm[z]
        downsample_factor = self._levels[z][level]["downsample_factor"]
        W = np.array(
            [
                [m["x"] / 1e6 * downsample_factor, 0, 0, 0],
                [0, m["y"] / 1e6 * downsample_factor, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ]
        )
        return W

    def load_metadata(self):
        self._levels = {}
        self._pixelsize_nm = {}
        for z in self._slides.keys():
            slide_id = self._slides[z]
            r = requests.get(self._wsi_service + f"/v1/slides/{slide_id}/info", stream=True)
            assert r.status_code == 200
            response = r.json()
            self._levels[z] = response["levels"]
            self._pixelsize_nm[z] = response["pixel_size_nm"]

    def get_region(
        self, level: int, start_x: int, start_y: int, size_x: int, size_y: int, z: int, image_format: str = "png"
    ) -> Image:
        if z == self._reference_slide_index:
            return self.fetch_region(level, start_x, start_y, size_x, size_y, z, image_format=image_format)
        start_R_px = [start_x, start_y]
        defX, defY, Wdef, _dimsX, _dimsY, _slide_id_R, _slide_id_T = self._deformation_tuple
        WR = self.get_world_matrix(level, self._reference_slide_index)
        WR_region = WR.copy()
        WR_region[0, 3] = start_x * WR[0, 0]
        WR_region[1, 3] = start_y * WR[1, 1]
        _WT, start_T_px, sizeT = self.get_target_region_area(WR_region, [size_x, size_y])
        undeformedTemplate = self.fetch_region(
            level, start_T_px[0], start_T_px[1], sizeT[0], sizeT[1], z, image_format=image_format
        )
        np_imgT = self.interpolate_region(
            undeformedTemplate,
            self.get_world_matrix(level, z),  # WT
            defX,
            defY,
            Wdef,
            (size_x, size_y),
            self.get_world_matrix(level, 0),  # WR
            start_T_px,
            start_R_px,
        )
        img_rgb = Image.fromarray(np_imgT.astype(np.uint8), mode="RGB")
        return img_rgb

    def get_slide_ids(self) -> dict:
        return self._slides

    @staticmethod
    def interpolate_region(
        undeformedTemplate: Image,
        WT: np.ndarray,
        defX: np.ndarray,
        defY: np.ndarray,
        Wdef: np.ndarray,
        size_out,
        WR: np.ndarray,
        start_T_px,
        start_R_px,
    ) -> np.array:
        rgb_channels = undeformedTemplate.split()
        channels = len(rgb_channels)
        deformedTemplate_one_channel = np.zeros((size_out[1], size_out[0]), order="C")
        deformedTemplate = np.zeros((size_out[1], size_out[0], channels), order="C")

        for c in range(channels):
            Deformation.interpolate_tile_single_channel(
                rgb_channels[c],
                WT,
                defX,
                defY,
                Wdef,
                size_out,
                WR,
                start_T_px,
                start_R_px,
                deformedTemplate_one_channel,
            )
            deformedTemplate[:, :, c] = deformedTemplate_one_channel[:, :]

        return deformedTemplate

    @staticmethod
    def interpolate_tile_single_channel(
        undeformedTemplate: Image,
        WT: np.ndarray,
        defX: np.ndarray,
        defY: np.ndarray,
        Wdef: np.ndarray,
        size_out,
        WR: np.ndarray,
        start_T_px,
        start_R_px,
        deformedTemplate: np.ndarray,
    ) -> None:
        channels = 1
        undeformedTemplate_np = np.array(undeformedTemplate, dtype=np.float64)
        undeformedTemplate_np_cptr = ffi.cast("double *", ffi.from_buffer(undeformedTemplate_np))

        deformedTemplate_cptr = ffi.cast("double *", ffi.from_buffer(deformedTemplate))
        defX = defX.transpose().copy(order="C")
        defY = defY.transpose().copy(order="C")
        defX_cptr = ffi.cast("double *", ffi.from_buffer(defX))
        defY_cptr = ffi.cast("double *", ffi.from_buffer(defY))
        WR = WR.copy(order="C")
        WR_cptr = ffi.cast("double *", ffi.from_buffer(WR))
        WTinv = np.linalg.inv(WT)
        WTInv_cptr = ffi.cast("double *", ffi.from_buffer(WTinv))
        Wdef_cptr = ffi.cast("double *", ffi.from_buffer(Wdef))
        Wdef_inv = np.linalg.inv(Wdef)
        Wdef_inv_cptr = ffi.cast("double *", ffi.from_buffer(Wdef_inv))
        # WR and WT are relative to the full template/reference image
        lib.interpolate_tile(
            undeformedTemplate_np_cptr,
            deformedTemplate_cptr,
            undeformedTemplate.width,
            undeformedTemplate.height,
            size_out[0],
            size_out[1],
            channels,
            start_T_px[0],
            start_T_px[1],
            start_R_px[0],
            start_R_px[1],
            WR_cptr,
            WTInv_cptr,
            defX_cptr,
            defY_cptr,
            Wdef_cptr,
            Wdef_inv_cptr,
            defX.shape[0],
            defX.shape[1],
        )

    @staticmethod
    def get_four_edges_world(WR, sourceSizePixel):
        pts = []
        sourceSizeWorld = np.dot(WR, np.append(sourceSizePixel, [0, 1]))
        pts.append(WR[:, 3].copy())
        pts.append(np.dot(WR, [sourceSizePixel[0], 0, 0, 1]))
        pts.append(np.dot(WR, [0, sourceSizePixel[1], 0, 1]))
        pts.append(sourceSizeWorld)
        return pts

    @staticmethod
    def transform_point(defInterp, WT, pts):
        tpts = np.zeros((len(pts), 2))
        tptsW = np.zeros((len(pts), 4))

        for i, pW in enumerate(pts):
            u = np.zeros(2)
            u[0] = defInterp[0](pW[0], pW[1])
            u[1] = defInterp[1](pW[0], pW[1])
            pW_t = np.array([0, 0, 0, 1.0])
            pW_t[0] = pW[0] + u[0]
            pW_t[1] = pW[1] + u[1]
            tp = np.linalg.solve(WT, pW_t)
            tptsW[i, :] = pW_t
            tpts[i, :] = tp[0:2]
        return tpts, tptsW
