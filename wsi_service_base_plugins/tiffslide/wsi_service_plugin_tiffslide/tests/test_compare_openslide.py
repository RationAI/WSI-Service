import numpy as np
import pytest
import requests

from wsi_service.models.v3.slide import SlideInfo
from wsi_service.tests.integration.plugin_example_tests.helpers import get_image


@pytest.mark.parametrize(
    "slide_id",
    [("8d32dba05a4558218880f06caf30d3ac"), ("f5f3a03b77fb5e0497b95eaff84e9a21")],
)
def test_compare_openslide_info(slide_id):
    response = requests.get(f"http://localhost:8080/v3/slides/{slide_id}/info?plugin=tiffslide")
    slide_info_tiffslide = SlideInfo.parse_obj(response.json())
    response = requests.get(f"http://localhost:8080/v3/slides/{slide_id}/info?plugin=openslide")
    slide_info_openslide = SlideInfo.parse_obj(response.json())
    assert slide_info_tiffslide == slide_info_openslide


@pytest.mark.parametrize(
    "slide_id, tiles",
    [
        ("8d32dba05a4558218880f06caf30d3ac", [(0, 73, 80), (1, 19, 21), (2, 3, 6)]),
        ("f5f3a03b77fb5e0497b95eaff84e9a21", [(0, 150, 164), (2, 40, 42), (7, 0, 1)]),
    ],
)
def test_compare_openslide_tile(slide_id, tiles):
    for level, x, y in tiles:
        response = requests.get(
            f"http://localhost:8080/v3/slides/{slide_id}/tile/level/{level}/tile/{x}/{y}?plugin=tiffslide",
            stream=True,
        )
        tile_tiffslide_pil = get_image(response)
        # tile_tiffslide_pil.save(f"{slide_id}_{level}_{x}_{y}_tiffslide.png")
        tile_tiffslide = np.array(tile_tiffslide_pil).astype(np.float64)
        response = requests.get(
            f"http://localhost:8080/v3/slides/{slide_id}/tile/level/{level}/tile/{x}/{y}?plugin=openslide&image_format=png",
            stream=True,
        )
        tile_openslide_pil = get_image(response)
        # tile_openslide_pil.save(f"{slide_id}_{level}_{x}_{y}_openslide.png")
        tile_openslide = np.array(tile_openslide_pil).astype(np.float64)
        mean_relative_error = np.mean(
            np.abs(tile_tiffslide[tile_openslide > 0] - tile_openslide[tile_openslide > 0])
            / tile_openslide[tile_openslide > 0]
        )
        # print(slide_id, level, x, y, mean_relative_error)
        # expect mean relative error < 5 %
        assert mean_relative_error < 0.05


@pytest.mark.parametrize(
    "slide_id, regions",
    [
        ("8d32dba05a4558218880f06caf30d3ac", [(0, 16000, 24000), (1, 4000, 6000), (2, 1000, 1500), (2, -200, -100)]),
        (
            "f5f3a03b77fb5e0497b95eaff84e9a21",
            [
                (0, 16000, 24000),
                (1, 8000, 12000),
                (2, 4000, 6000),
                (2, -200, -100),
                (3, 2000, 3000),
                (4, 1000, 1500),
                (9, 0, 0),
            ],
        ),
    ],
)
def test_compare_openslide_region(slide_id, regions):
    for level, x, y in regions:
        response = requests.get(
            f"http://localhost:8080/v3/slides/{slide_id}/region/level/{level}/start/{x}/{y}/size/512/512?plugin=tiffslide&image_format=png",
            stream=True,
        )
        tile_tiffslide_pil = get_image(response)
        # tile_tiffslide_pil.save(f"{slide_id}_{level}_{x}_{y}_tiffslide.png")
        tile_tiffslide = np.array(tile_tiffslide_pil).astype(np.float64)
        response = requests.get(
            f"http://localhost:8080/v3/slides/{slide_id}/region/level/{level}/start/{x}/{y}/size/512/512?plugin=openslide&image_format=png",
            stream=True,
        )
        tile_openslide_pil = get_image(response)
        # tile_openslide_pil.save(f"{slide_id}_{level}_{x}_{y}_openslide.png")
        tile_openslide = np.array(tile_openslide_pil).astype(np.float64)
        mean_relative_error = np.mean(
            np.abs(tile_tiffslide[tile_openslide > 0] - tile_openslide[tile_openslide > 0])
            / tile_openslide[tile_openslide > 0]
        )
        # print(slide_id, level, x, y, mean_relative_error)
        # expect mean relative error < 5 %
        assert mean_relative_error < 0.05
