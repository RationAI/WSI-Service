# tifffile plugin

The plugin reads TIFF layouts that tifffile exposes as logical series with `X` and `Y` axes and optional channel/Z axes.

Supported layouts include:

- `ZCYX`: one grayscale page per channel and Z layer.
- `CYX`: one grayscale page per channel.
- `ZYX`: one grayscale page per Z layer.
- `ZYXS`: one RGB/RGBA page per Z layer, such as ImageJ RGB Z-stacks.
- Chunky sample pages such as `YXS` or `CYX` where channels are stored in `SamplesPerPixel`.

For Z-stacks, the plugin reports the logical Z count in the base extent and every pyramid level, and accepts the `z` query parameter for region and tile reads. ImageJ `spacing` metadata is exposed as `pixel_size_nm.z` when its unit is recognized.

For tiled TIFFs, the native tile dimensions are reported. For untiled TIFFs, the full level is reported as one effective tile when its largest dimension is at most 2048 pixels; larger levels use a 512x512 API tile fallback.

Ordinary single-plane RGB/YCbCr TIFFs remain delegated to the existing WSI plugins. This avoids changing plugin selection for conventional RGB slides.
