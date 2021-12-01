import os
import tempfile

import pytest
from fastapi import HTTPException

from wsi_service.local_mapper import LocalMapper


def test_get_cases_no_data():
    localmapper = LocalMapper(tempfile.mkdtemp())
    cases = localmapper.get_cases()
    assert len(cases) == 0


def test_get_cases_two_empty_cases():
    tmp_dir = tempfile.mkdtemp()
    os.mkdir(os.path.join(tmp_dir, "case0"))
    os.mkdir(os.path.join(tmp_dir, "case1"))
    localmapper = LocalMapper(tmp_dir)
    cases = localmapper.get_cases()
    assert len(cases) == 2


def test_get_available_slides_empty_case():
    tmp_dir = tempfile.mkdtemp()
    os.mkdir(os.path.join(tmp_dir, "case0"))
    localmapper = LocalMapper(tmp_dir)
    cases = localmapper.get_cases()
    case_id = cases[0].id
    slides = localmapper.get_slides(case_id)
    assert len(slides) == 0


def test_get_case_invalid_dir():
    with pytest.raises(HTTPException):
        LocalMapper("/invalid/dir")


def test_get_cases_get_slides_valid():
    test_data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
    localmapper = LocalMapper(test_data_dir)
    cases = localmapper.get_cases()
    assert len(cases) == 1
    case_id = cases[0].id
    slides = localmapper.get_slides(case_id)
    assert len(slides) == 3
    assert slides[0].id == "14b5c5dab96b540bba23b08429592bcf"
    assert slides[0].local_id == "CMU-1-small.tiff"
    slide = localmapper.get_slide(slides[0].id)
    assert slide.id == slides[0].id
    assert slide.local_id == slides[0].local_id
