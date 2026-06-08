import os
import pathlib

import tifffile

from wsi_service_plugin_tifffile.slide import Slide

priority = 2

_OME_SUFFIXES = ("ome.tif", "ome.tiff", "ome.tf2", "ome.tf8", "ome.btf")
_TIFF_SUFFIXES = (".tif", ".tiff", ".tf2", ".tf8", ".btf")

# tifffile.PHOTOMETRIC values
_PHOTOMETRIC_RGB = 2
_PHOTOMETRIC_YCBCR = 6


def is_supported(filepath):
    if not os.path.isfile(filepath):
        return False

    filename = pathlib.Path(filepath).name.lower()
    if any(filename.endswith(s) for s in _OME_SUFFIXES):
        return True

    suffix = pathlib.Path(filepath).suffix.lower()
    if suffix not in _TIFF_SUFFIXES:
        return False

    try:
        with tifffile.TiffFile(filepath) as tf:
            if tf.is_ome:
                return True

            series = tf.series[0]
            keyframe = series.keyframe
            samples = int(getattr(keyframe, "samplesperpixel", 1) or 1)
            photometric = int(getattr(keyframe, "photometric", 0) or 0)

            # Plain RGB(A) — let tiffslide handle it.
            if photometric in (_PHOTOMETRIC_RGB, _PHOTOMETRIC_YCBCR) and samples in (3, 4):
                return False

            # Chunky multichannel (SamplesPerPixel > 1, non-RGB photometric).
            if samples > 1:
                return True

            # Page-per-channel: multi-page series with a channel-like axis.
            axes = str(getattr(series, "axes", "") or "")
            shape = tuple(getattr(series, "shape", ()) or ())
            for ch in ("C", "S"):
                if ch in axes:
                    idx = axes.index(ch)
                    if idx < len(shape) and shape[idx] > 1:
                        return True

            return False
    except Exception:
        return False


async def open(filepath):
    return await Slide.create(filepath)
