import numpy as np
from PIL import Image
from PIL.ImageStat import Stat

from wsi_service.models.v3.slide import SlideColor
from wsi_service.utils.image_utils import (
    convert_int_to_rgba_array,
    convert_narray_to_pil_image,
    convert_narray_uintX_to_uint8,
    convert_rgba_array_to_int,
    get_multi_channel_as_rgb,
    get_requested_channels_as_array,
    get_requested_channels_as_rgb_array,
    get_single_channel,
    rgba_to_rgb_with_background_color,
)

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
    result = c_array == np.array([[71, 255, 3], [255, 36, 83], [255, 255, 3]])
    assert result.all()

    c_array = convert_narray_uintX_to_uint8(ndarray, 16, 100, 10000)
    assert c_array.dtype == np.uint8
    result = c_array == np.array([[115, 255, 2], [255, 58, 134], [255, 255, 3]])
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


def test_rgba_to_rgb_with_background_color():
    # expect completely transperant image to become white
    image_rgba = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    image_rgb = rgba_to_rgb_with_background_color(image_rgba, padding_color=(255, 255, 255))
    assert sum(Stat(image_rgb).mean) / 3 == 255
    # expect intransperant image to not change
    image_rgba = Image.new("RGBA", (256, 256), (0, 0, 0, 255))
    image_rgb = rgba_to_rgb_with_background_color(image_rgba, padding_color=(255, 255, 255))
    assert sum(Stat(image_rgb).mean) / 3 == 0
    # expect partly transperant image to only change transparent part
    image_rgba = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    image_rgba_half = Image.new("RGBA", (256, 128), (0, 0, 0, 255))
    Image.Image.paste(image_rgba, image_rgba_half)
    image_rgb = rgba_to_rgb_with_background_color(image_rgba, padding_color=(255, 255, 255))
    # expect partly transperant image to only change transparent part
    image_rgba = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    image_rgba_half = Image.new("RGBA", (256, 128), (0, 0, 0, 255))
    Image.Image.paste(image_rgba, image_rgba_half)
    image_rgb = rgba_to_rgb_with_background_color(image_rgba, padding_color=(255, 255, 255))
    assert sum(Stat(image_rgb).mean) / 3 == 127.5
