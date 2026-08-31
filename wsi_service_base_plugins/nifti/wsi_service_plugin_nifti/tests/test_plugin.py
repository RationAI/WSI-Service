from io import BytesIO

import nibabel as nib
import numpy as np
import pytest
import wsi_service_plugin_nifti as plugin
from fastapi import HTTPException
from PIL import Image

from wsi_service.plugins import get_plugins_overview, is_supported_format, load_slide
from wsi_service.utils.app_utils import make_response
from wsi_service.utils.image_utils import get_extended_region


def save_volume(tmp_path, data, suffix=".nii", image_class=nib.Nifti1Image, window=None, units="mm"):
    path = tmp_path / f"volume{suffix}"
    image = image_class(data, np.diag([0.5, 0.75, 2, 1]))
    image.header.set_xyzt_units(units)
    if window is not None:
        image.header["cal_min"], image.header["cal_max"] = window
    nib.save(image, path)
    return path


@pytest.mark.asyncio
@pytest.mark.parametrize("suffix", [".nii", ".nii.gz", ".NII", ".NII.GZ"])
@pytest.mark.parametrize("image_class", [nib.Nifti1Image, nib.Nifti2Image])
async def test_discovery_metadata_and_z_regions(tmp_path, suffix, image_class):
    data = np.arange(24, dtype=np.int16).reshape(4, 3, 2)
    path = save_volume(tmp_path, data, suffix, image_class, window=(0, 23))
    assert plugin.is_supported(path)
    assert is_supported_format(path)
    slide = await load_slide(path)
    try:
        assert slide.plugin == "nifti"
        info = await slide.get_info()
        assert (info.extent.x, info.extent.y, info.extent.z) == (4, 3, 2)
        assert info.num_levels == 1
        assert info.levels[0].extent.z == 2
        assert info.pixel_size_nm.model_dump() == {"x": 500000, "y": 750000, "z": 2000000}
        assert info.channel_depth == 8
        assert len(info.channels) == 3
        region = await slide.get_region(0, 1, 1, 2, 2, z=1)
        expected = np.rint(data[1:3, 1:3, 1].T / 23 * 255).astype(np.uint8)
        np.testing.assert_array_equal(np.asarray(region), np.repeat(expected[..., None], 3, axis=2))
        assert not slide._image.in_memory
        assert any(p.name == "nifti" for p in get_plugins_overview())
    finally:
        await slide.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("shape", [(5, 3), (5, 3, 1), (5, 3, 2, 1), (5, 3, 2, 1, 1)])
async def test_2d_and_singleton_axes(tmp_path, shape):
    data = np.arange(np.prod(shape), dtype=np.float32).reshape(shape)
    slide = await plugin.open(save_volume(tmp_path, data))
    try:
        image = await slide.get_region(0, 0, 0, 5, 3)
        assert image.size == (5, 3)
        assert image.mode == "RGB"
    finally:
        await slide.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("units,factor", [("meter", 1e9), ("mm", 1e6), ("micron", 1e3), ("unknown", None)])
async def test_spacing_units(tmp_path, units, factor):
    slide = await plugin.open(save_volume(tmp_path, np.zeros((2, 3, 4), dtype=np.uint8), units=units))
    try:
        spacing = (await slide.get_info()).pixel_size_nm
        assert spacing.x == (0.5 * factor if factor else -1)
        assert spacing.y == (0.75 * factor if factor else -1)
        assert spacing.z == (2 * factor if factor else -1)
    finally:
        await slide.close()


@pytest.mark.asyncio
async def test_header_scaling_and_calibration(tmp_path):
    data = np.array([[-10, 0, 10], [20, 30, 40]], dtype=np.int16)
    path = tmp_path / "scaled.nii"
    image = nib.Nifti1Image(data, np.eye(4))
    image.header.set_slope_inter(2, -5)
    image.header["cal_min"], image.header["cal_max"] = -5, 55
    nib.save(image, path)
    slide = await plugin.open(path)
    try:
        region = await slide.get_region(0, 0, 0, 2, 3)
        expected = np.array([[0, 170], [0, 255], [85, 255]], dtype=np.uint8)
        np.testing.assert_array_equal(np.asarray(region)[:, :, 0], expected)
    finally:
        await slide.close()


@pytest.mark.asyncio
async def test_fallback_window_is_shared_across_regions_and_slices(tmp_path):
    data = np.array([[[0, 100], [25, 75]], [[50, 50], [75, 25]]], dtype=np.float32)
    slide = await plugin.open(save_volume(tmp_path, data, ".nii.gz"))
    try:
        assert slide._window is None
        left = await slide.get_region(0, 0, 0, 1, 2, z=0)
        right = await slide.get_region(0, 1, 0, 1, 2, z=0)
        other = await slide.get_region(0, 0, 0, 2, 2, z=1)
        np.testing.assert_array_equal(np.asarray(left)[:, :, 0], [[0], [64]])
        np.testing.assert_array_equal(np.asarray(right)[:, :, 0], [[128], [191]])
        np.testing.assert_array_equal(np.asarray(other)[:, :, 0], [[255, 128], [191, 64]])
        assert slide._window == (0, 100)
        assert not slide._image.in_memory
    finally:
        await slide.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [np.full((2, 3), 7, dtype=np.float32), np.full((2, 3), np.nan)])
async def test_constant_or_nonfinite_volumes(tmp_path, data):
    slide = await plugin.open(save_volume(tmp_path, data))
    try:
        assert not np.asarray(await slide.get_region(0, 0, 0, 2, 3)).any()
    finally:
        await slide.close()


@pytest.mark.asyncio
async def test_nonfinite_voxels_are_black(tmp_path):
    data = np.array([[np.nan, np.inf, -np.inf], [0, 50, 100]], dtype=np.float32)
    slide = await plugin.open(save_volume(tmp_path, data))
    try:
        region = await slide.get_region(0, 0, 0, 2, 3)
        np.testing.assert_array_equal(np.asarray(region)[:, :, 0], [[0, 0], [0, 128], [0, 255]])
    finally:
        await slide.close()


@pytest.mark.asyncio
async def test_tiles_padding_and_thumbnail(tmp_path):
    data = np.zeros((514, 4, 3), dtype=np.int16)
    data[:, :, 1] = 50
    data[:, :, 2] = 100
    slide = await plugin.open(save_volume(tmp_path, data, window=(0, 100)))
    try:
        tile = await slide.get_tile(0, 1, 0, padding_color=(1, 2, 3), z=2)
        assert tile.size == (512, 4)
        assert tile.getpixel((1, 0)) == (255, 255, 255)
        assert tile.getpixel((2, 0)) == (1, 2, 3)
        region = await slide.get_region(0, -1, -1, 3, 3, (1, 2, 3), z=1)
        assert region.getpixel((0, 0)) == (1, 2, 3)
        assert region.getpixel((1, 1)) == (128, 128, 128)
        outside = await slide.get_tile(0, -100, 100, (1, 2, 3))
        assert outside.getextrema() == ((1, 1), (2, 2), (3, 3))
        thumb = await slide.get_thumbnail(100, 100)
        assert thumb.width <= 100 and thumb.height <= 100
        assert thumb.getpixel((0, 0)) == (128, 128, 128)
    finally:
        await slide.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "shape,dtype", [((4,), "int16"), ((2, 3, 4, 2), "float32"), ((2, 3, 4, 1, 2), "float32"), ((2, 3), "complex64")]
)
async def test_unsupported_volumes(tmp_path, shape, dtype):
    with pytest.raises(HTTPException, match="unsupported") as error:
        await plugin.open(save_volume(tmp_path, np.zeros(shape, dtype=dtype)))
    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_corrupt_file(tmp_path):
    path = tmp_path / "broken.nii"
    path.write_bytes(b"not a nifti file")
    with pytest.raises(HTTPException, match="Unable to read NIfTI"):
        await plugin.open(path)


@pytest.mark.asyncio
async def test_invalid_requests_and_missing_associated_images(tmp_path):
    slide = await plugin.open(save_volume(tmp_path, np.zeros((3, 4, 2), dtype=np.uint8)))
    try:
        for kwargs in ({"level": 1}, {"level": -1}, {"z": -1}, {"z": 2}, {"size_x": 0}):
            args = dict(level=0, start_x=0, start_y=0, size_x=2, size_y=2)
            args.update(kwargs)
            with pytest.raises(HTTPException) as error:
                await slide.get_region(**args)
            assert error.value.status_code == 400
        for method in (slide.get_label, slide.get_macro, slide.get_icc_profile):
            with pytest.raises(HTTPException) as error:
                await method()
            assert error.value.status_code == 404
        with pytest.raises(HTTPException) as error:
            await slide.get_region(0, 0, 0, 1, 1, icc_profile_intent="perceptual", icc_profile_strict=True)
        assert error.value.status_code == 412
        await slide.get_region(0, 0, 0, 1, 1, icc_profile_intent="perceptual")
    finally:
        await slide.close()
    await slide.close()
    with pytest.raises(HTTPException, match="closed"):
        await slide.get_region(0, 0, 0, 1, 1)


@pytest.mark.asyncio
@pytest.mark.parametrize("image_format", ["png", "jpeg", "tiff"])
async def test_service_encoding_and_padding(tmp_path, image_format):
    slide = await load_slide(save_volume(tmp_path, np.arange(12, dtype=np.int16).reshape(3, 4)))
    try:
        region = await get_extended_region(
            slide.get_region, await slide.get_info(), 0, -1, -1, 4, 5, padding_color=(20, 30, 40)
        )
        response = make_response(slide, region, image_format, 100)
        assert response.media_type == f"image/{image_format}"
        if image_format == "tiff":
            import tifffile

            decoded = tifffile.imread(BytesIO(response.body))
            assert decoded.shape == (3, 5, 4)
            np.testing.assert_array_equal(decoded[:, 0, 0], [20, 30, 40])
        else:
            decoded = Image.open(BytesIO(response.body))
            assert decoded.size == (4, 5)
            if image_format == "png":
                assert decoded.getpixel((0, 0)) == (20, 30, 40)
    finally:
        await slide.close()


def test_detection_and_mapper_extensions(tmp_path, monkeypatch):
    from wsi_service.mapper_iterator.iterator.control_extensions import get_extension, is_allowed_extension

    path = save_volume(tmp_path, np.zeros((2, 3), dtype=np.uint8), ".nii.gz")
    assert get_extension(str(path)) == ".nii.gz"
    assert get_extension("SCAN.NII.GZ") == ".nii.gz"
    assert is_allowed_extension(".nii")
    assert is_allowed_extension(".nii.gz")
    assert not plugin.is_supported(tmp_path / "missing.nii")
    assert not plugin.is_supported(tmp_path)
    assert not plugin.is_supported(tmp_path / "image.tiff")
    monkeypatch.setenv("WS_PLUGIN_PRIORITY_NIFTI", "-1")
    assert not is_supported_format(path)


@pytest.mark.asyncio
async def test_http_routes_with_local_mapper(tmp_path):
    from fastapi import FastAPI
    from httpx import AsyncClient

    from wsi_service.api.v3.slides import add_routes_slides, api_integration
    from wsi_service.paths_mapper import PathsMapper
    from wsi_service.settings import Settings
    from wsi_service.slide_manager import SlideManager

    data = np.zeros((8, 6, 3), dtype=np.int16)
    data[:, :, 1] = 50
    data[:, :, 2] = 100
    path = save_volume(tmp_path, data, ".nii.gz", window=(0, 100))
    settings = Settings(data_dir=str(tmp_path))
    manager = SlideManager("", str(tmp_path), 600, 4).with_local_mapper(PathsMapper(str(tmp_path)))
    app = FastAPI()
    add_routes_slides(app, settings, manager)
    app.dependency_overrides[api_integration.global_depends().dependency] = lambda: None
    params = {"slide_id": path.name, "plugin": "nifti", "image_format": "png", "z": 1}
    try:
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            info = await client.get("/slides/info", params=params)
            assert info.status_code == 200
            assert info.json()["extent"] == {"x": 8, "y": 6, "z": 3}
            assert info.json()["raw_download"] is True
            for endpoint, size in [
                ("/slides/region/level/0/start/0/0/size/4/3", (4, 3)),
                ("/slides/tile/level/0/tile/0/0", (8, 6)),
                ("/slides/thumbnail/max_size/4/4", (4, 3)),
            ]:
                response = await client.get(endpoint, params=params)
                assert response.status_code == 200, response.text
                rendered = Image.open(BytesIO(response.content))
                assert rendered.size == size
                assert rendered.getpixel((0, 0)) == (128, 128, 128)
            response = await client.get("/slides/region/level/0/start/0/0/size/4/3", params={**params, "z": 3})
            assert response.status_code == 422
            response = await client.get(
                "/slides/region/level/0/start/-1/-1/size/4/3", params={**params, "padding_color": "#010203"}
            )
            assert response.status_code == 200
            padded = Image.open(BytesIO(response.content))
            assert padded.getpixel((0, 0)) == (1, 2, 3)
            assert padded.getpixel((1, 1)) == (128, 128, 128)
    finally:
        for cache_id, cached in list(manager.slide_cache.get_all().items()):
            cached.timer.cancel()
            await manager._close_slide(cache_id)
