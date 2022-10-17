import numpy as np

from wsi_service.image_utils import (
    convert_int_to_rgba_array,
    convert_narray_to_pil_image,
    convert_narray_uintX_to_uint8,
    convert_rgba_array_to_int,
    get_multi_channel_as_rgb,
    get_requested_channels_as_array,
    get_requested_channels_as_rgb_array,
    get_single_channel,
)
from wsi_service.models.v3.slide import SlideColor

ndarray = np.array(
    [
        [[4573, 56445, 213], [24521, 2352, 5341], [34013, 64342, 234]],
        [[4573, 56445, 213], [24521, 2352, 5341], [34013, 64342, 234]],
        [[4573, 56445, 213], [24521, 2352, 5341], [34013, 64342, 234]],
    ],
    dtype=np.uint16,
)


def test_convert_narray_uintX_to_uint8():
    c_array = convert_narray_uintX_to_uint8(ndarray, 16)
    assert c_array.dtype == np.uint8
    result = c_array == np.array([[71, 110, 3], [125, 36, 83], [17, 233, 3]])
    assert result.all()

    c_array = convert_narray_uintX_to_uint8(ndarray, 16, 2, 3)
    assert c_array.dtype == np.uint8
    result = c_array == np.array([[97, 129, 185], [189, 240, 97], [97, 142, 178]])
    assert result.all()


def test_convert_int_to_rgba_array():
    array = convert_int_to_rgba_array(16777215)
    assert array == [0, 255, 255, 255]
    array = convert_int_to_rgba_array(65280)
    assert array == [0, 0, 255, 0]
    array = convert_int_to_rgba_array(2850124)
    assert array == [0, 43, 125, 76]


def test_convert_rgba_array_to_int():
    res = convert_rgba_array_to_int([0, 255, 255, 255])
    assert res == 16777215
    res = convert_rgba_array_to_int([0, 0, 255, 0])
    assert res == 65280
    res = convert_rgba_array_to_int([0, 43, 125, 76])
    assert res == 2850124


def test_convert_narray_to_pil_image():
    rgb_array = get_requested_channels_as_rgb_array(ndarray, None, None)
    pil_image = convert_narray_to_pil_image(rgb_array)
    assert pil_image.size == (3, 3)


def test_get_multi_channel_as_rgb():
    rgb_array = get_multi_channel_as_rgb(ndarray)
    assert len(rgb_array) == 3


def test_get_single_channel():
    single_channel = get_single_channel(ndarray, 0, SlideColor(r=255, g=0, b=0, a=0))
    assert len(single_channel) == 3
    red_channel = single_channel[0] == ndarray[0]
    assert red_channel.all()
    green_channel = single_channel[1] == np.zeros((3, 3))
    assert green_channel.all()


def test_get_requested_channels_as_array():
    req_channels = get_requested_channels_as_array(ndarray, [0, 1])
    assert len(req_channels) == 2
