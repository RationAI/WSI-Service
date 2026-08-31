# NIfTI plugin

Reads single-file NIfTI-1 and NIfTI-2 images (`.nii` and `.nii.gz`) using
[NiBabel](https://nipy.org/nibabel/nifti_images.html). Install with the service's
development dependencies (`poetry install`) or install this directory into an
existing WSI Service environment. Both Docker builds include the plugin.

The plugin is discovered as `nifti`. It can be explicitly selected with
`plugin=nifti`, and disabled with `WS_PLUGIN_PRIORITY_NIFTI=-1`.

## Supported images and coordinates

- Real-valued scalar 2D and 3D volumes. Extra dimensions are accepted only when
  their size is one. Non-singleton time/vector axes and complex/RGB voxel types
  are rejected rather than silently dropping data.
- Stored voxel axes map directly to service `x`, `y`, and `z`; `z` is zero-based
  and defaults to zero. The affine is not used to rotate, flip, or resample the
  volume into an anatomical orientation. These are voxel planes, not necessarily
  anatomical axial slices.
- One native resolution level (`level=0`), with tiles at most 512 × 512 pixels.
- Header voxel spacing is converted from meters, millimeters, or microns to
  nanometers, including Z spacing. Unknown units/spacing are reported as `-1`.
- Thumbnails show the middle Z plane. Labels, macros, and ICC profiles return
  404. Strict ICC processing requests return 412; non-strict requests are no-ops.

For example, request slice 12 with:

```text
/v3/slides/region/level/0/start/0/0/size/256/256?slide_id=<slide_id>&plugin=nifti&z=12&image_format=png
/v3/slides/tile/level/0/tile/0/0?slide_id=<slide_id>&plugin=nifti&z=12
```

## Rendering and resource use

This is a **display plugin**: regions, tiles, and thumbnails contain 8-bit RGB
grayscale, with identical red, green, and blue intensities. The metadata reports
three display channels at depth 8. TIFF responses also contain rendered pixels,
not the original signed or floating-point voxel values. Use the original NIfTI
file for quantitative analysis.

NiBabel applies the header's `scl_slope` and `scl_inter` before rendering. A valid
`cal_min`/`cal_max` defines the display range; otherwise the first image request
scans finite voxel values for a volume-wide minimum and maximum. The resulting
range is reused across all tiles and slices for the lifetime of the slide handle.
Values outside it are clipped; constant volumes and non-finite voxels render black.
Padding uses the service's RGB padding color.

Opening and metadata requests read only the header. Voxel reads use array-proxy
slices, and the fallback intensity scan uses bounded blocks instead of loading
the whole volume. Reads run outside the async event loop. The initial scan can
be slow for large compressed files; uncompressed `.nii` is preferable for frequent
random access. No synthetic pyramid is generated.

Run the self-contained tests from the repository root:

```sh
poetry run pytest wsi_service_base_plugins/nifti/wsi_service_plugin_nifti/tests
```
