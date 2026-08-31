import asyncio
from threading import Lock

import nibabel as nib
import numpy as np
from fastapi import HTTPException
from PIL import Image

from wsi_service.models.v3.slide import SlideExtent, SlideInfo, SlideLevel, SlidePixelSizeNm
from wsi_service.singletons import settings
from wsi_service.slide import Slide as BaseSlide
from wsi_service.utils.slide_utils import get_rgb_channel_list


class Slide(BaseSlide):
    """Render scalar NIfTI volumes in their stored voxel order as grayscale RGB."""

    async def open(self, filepath):
        self._lock = Lock()
        self._image = None
        await asyncio.to_thread(self._open, filepath)

    def _open(self, filepath):
        try:
            image = nib.load(str(filepath), mmap="r", keep_file_open=False)
        except (OSError, ValueError, nib.filebasedimages.ImageFileError) as exc:
            raise HTTPException(status_code=400, detail=f"Unable to read NIfTI image: {exc}") from exc
        if not isinstance(image, (nib.Nifti1Image, nib.Nifti2Image)):
            raise HTTPException(status_code=400, detail="Expected a single-file NIfTI-1 or NIfTI-2 image.")
        shape = image.shape
        if len(shape) < 2 or any(size < 1 for size in shape) or any(size != 1 for size in shape[3:]):
            raise HTTPException(
                status_code=400,
                detail="NIfTI supports 2D/3D scalar images only; non-singleton time or vector axes are unsupported.",
            )
        if image.get_data_dtype().kind not in "uif":
            raise HTTPException(status_code=400, detail="Complex and RGB/vector NIfTI voxel types are unsupported.")

        width, height = shape[:2]
        depth = shape[2] if len(shape) > 2 else 1
        extent = SlideExtent(x=width, y=height, z=depth)
        units = image.header.get_xyzt_units()[0]
        unit_nm = {"meter": 1e9, "mm": 1e6, "micron": 1e3}.get(units)
        zooms = image.header.get_zooms()

        def spacing(axis):
            if unit_nm is None or axis >= len(zooms) or not np.isfinite(zooms[axis]) or zooms[axis] <= 0:
                return -1
            return float(zooms[axis]) * unit_nm

        self.slide_info = SlideInfo(
            id="",
            channels=get_rgb_channel_list(),
            channel_depth=8,
            extent=extent,
            num_levels=1,
            pixel_size_nm=SlidePixelSizeNm(x=spacing(0), y=spacing(1), z=spacing(2)),
            tile_extent=SlideExtent(x=min(width, 512), y=min(height, 512), z=1),
            levels=[SlideLevel(extent=extent, downsample_factor=1.0)],
            format="nifti",
        )
        low, high = float(image.header["cal_min"]), float(image.header["cal_max"])
        self._window = (low, high) if np.isfinite([low, high]).all() and low < high else None
        self._image = image

    async def close(self):
        await asyncio.to_thread(self._close)

    def _close(self):
        with self._lock:
            if self._image is not None:
                self._image.uncache()
                self._image = None

    async def get_info(self):
        return self.slide_info

    def _read(self, x, y, z):
        # NiBabel applies scl_slope/scl_inter through its proxy. Slice before
        # converting to avoid materializing the full volume in memory.
        indices = (x, y)
        if len(self._image.shape) > 2:
            indices += (z,)
        indices += (0,) * max(0, len(self._image.shape) - 3)
        return np.asarray(self._image.dataobj[indices], dtype=np.float64).T

    def _get_window(self):
        if self._window is None:
            low, high = np.inf, -np.inf
            extent = self.slide_info.extent
            # Scan once, in bounded blocks, so tiles and Z layers use the same
            # contrast. Header calibration avoids this scan when available.
            block_width = min(extent.x, 1024)
            block_height = max(1, 1_048_576 // block_width)
            for z in range(extent.z):
                for y in range(0, extent.y, block_height):
                    for x in range(0, extent.x, block_width):
                        values = self._read(slice(x, x + block_width), slice(y, y + block_height), z)
                        finite = values[np.isfinite(values)]
                        if finite.size:
                            low = min(low, float(finite.min()))
                            high = max(high, float(finite.max()))
            self._window = (low, high) if np.isfinite([low, high]).all() else (0.0, 0.0)
        return self._window

    def _render(self, values):
        low, high = self._get_window()
        if high <= low:
            gray = np.zeros(values.shape, dtype=np.uint8)
        else:
            with np.errstate(invalid="ignore", over="ignore"):
                clipped = np.clip(values, low, high)
                if np.isfinite(high - low):
                    scaled = (clipped - low) / (high - low)
                else:
                    # Finite float64 endpoints can still overflow on subtraction.
                    scale = max(abs(low), abs(high))
                    scaled = (clipped / scale - low / scale) / (high / scale - low / scale)
            scaled = np.where(np.isfinite(values), scaled, 0)
            gray = np.rint(np.clip(scaled, 0, 1) * 255).astype(np.uint8)
        return Image.fromarray(gray).convert("RGB")

    @staticmethod
    def _check_icc(intent, strict):
        if intent is not None and strict:
            raise HTTPException(status_code=412, detail="ICC Profile not available.")

    async def get_region(
        self,
        level,
        start_x,
        start_y,
        size_x,
        size_y,
        padding_color=None,
        z=0,
        icc_profile_intent=None,
        icc_profile_strict=False,
    ):
        self._check_icc(icc_profile_intent, icc_profile_strict)
        if level != 0:
            raise HTTPException(status_code=400, detail="NIfTI images have only level 0.")
        if not 0 <= z < self.slide_info.extent.z:
            raise HTTPException(status_code=400, detail=f"Invalid NIfTI Z layer: {z}.")
        if size_x <= 0 or size_y <= 0:
            raise HTTPException(status_code=400, detail="Region dimensions must be positive.")
        color = settings.padding_color if padding_color is None else padding_color
        return await asyncio.to_thread(self._get_region, start_x, start_y, size_x, size_y, color, z)

    def _get_region(self, start_x, start_y, size_x, size_y, color, z):
        with self._lock:
            if self._image is None:
                raise HTTPException(status_code=400, detail="NIfTI image is closed.")
            result = Image.new("RGB", (size_x, size_y), color)
            x0, y0 = max(start_x, 0), max(start_y, 0)
            x1 = min(start_x + size_x, self.slide_info.extent.x)
            y1 = min(start_y + size_y, self.slide_info.extent.y)
            if x0 < x1 and y0 < y1:
                values = self._read(slice(x0, x1), slice(y0, y1), z)
                result.paste(self._render(values), (x0 - start_x, y0 - start_y))
            return result

    async def get_tile(
        self,
        level,
        tile_x,
        tile_y,
        padding_color=None,
        z=0,
        icc_profile_intent=None,
        icc_profile_strict=False,
    ):
        tile = self.slide_info.tile_extent
        return await self.get_region(
            level,
            tile_x * tile.x,
            tile_y * tile.y,
            tile.x,
            tile.y,
            padding_color,
            z,
            icc_profile_intent,
            icc_profile_strict,
        )

    async def get_thumbnail(self, max_x, max_y, icc_profile_intent=None, icc_profile_strict=False):
        self._check_icc(icc_profile_intent, icc_profile_strict)
        if max_x <= 0 or max_y <= 0:
            raise HTTPException(status_code=400, detail="Thumbnail dimensions must be positive.")
        return await asyncio.to_thread(self._get_thumbnail, max_x, max_y)

    def _get_thumbnail(self, max_x, max_y):
        with self._lock:
            if self._image is None:
                raise HTTPException(status_code=400, detail="NIfTI image is closed.")
            extent = self.slide_info.extent
            scale = min(1.0, max_x / extent.x, max_y / extent.y)
            target_size = (max(1, round(extent.x * scale)), max(1, round(extent.y * scale)))
            step = max(1, int(1 / scale))
            values = self._read(slice(None, None, step), slice(None, None, step), extent.z // 2)
            thumbnail = self._render(values)
            return thumbnail.resize(target_size, Image.Resampling.LANCZOS)

    async def get_label(self):
        raise HTTPException(status_code=404, detail="Associated image label does not exist.")

    async def get_macro(self, icc_profile_intent=None, icc_profile_strict=False):
        raise HTTPException(status_code=404, detail="Associated image macro does not exist.")

    async def get_icc_profile(self):
        raise HTTPException(status_code=404, detail="ICC Profile not available.")
