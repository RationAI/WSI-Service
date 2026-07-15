import os
import pathlib

import tifffile

from wsi_service_plugin_tifffile.slide import Slide

priority = 2

_OME_SUFFIXES = (".ome.tif", ".ome.tiff", ".ome.tf2", ".ome.tf8", ".ome.btf")
_TIFF_SUFFIXES = (".tif", ".tiff", ".tf2", ".tf8", ".btf")

# tifffile.PHOTOMETRIC values
_PHOTOMETRIC_RGB = 2
_PHOTOMETRIC_YCBCR = 6


def _has_supported_axis_layout(series, samples):
    axes = str(getattr(series, "axes", "") or "")
    shape = tuple(getattr(series, "shape", ()) or ())

    for index, axis_name in enumerate(axes):
        if axis_name in ("X", "Y"):
            continue
        if axis_name in ("C", "S", "Z") and index < len(shape) and shape[index] > 1:
            if axis_name in ("C", "S"):
                return True
            if axis_name == "Z":
                return True
        if axis_name not in ("X", "Y", "C", "S", "Z") and index < len(shape) and shape[index] > 1:
            return False

    return samples > 1


def _has_nontrivial_axis(series, axis_name):
    axes = str(getattr(series, "axes", "") or "")
    shape = tuple(getattr(series, "shape", ()) or ())
    try:
        index = axes.index(axis_name)
    except ValueError:
        return False
    return index < len(shape) and shape[index] > 1


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

            # Plain RGB(A) — let tiffslide handle it. RGB Z-stacks are different:
            # tiffslide/openslide do not expose their individual Z pages reliably.
            if (
                photometric in (_PHOTOMETRIC_RGB, _PHOTOMETRIC_YCBCR)
                and samples in (3, 4)
                and not _has_nontrivial_axis(series, "Z")
            ):
                return False

            # Chunky multichannel (SamplesPerPixel > 1, non-RGB photometric).
            if samples > 1:
                return True

            return _has_supported_axis_layout(series, samples)
    except Exception:
        return False


async def open(filepath):
    return await Slide.create(filepath)
