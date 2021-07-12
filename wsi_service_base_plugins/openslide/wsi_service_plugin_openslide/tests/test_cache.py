import time

import psutil
import requests

slide_ids = [
    "4b0ec5e0ec5e5e05ae9e500857314f20",
    "f863c2ef155654b1af0387acc7ebdb60",
    "c801ce3d1de45f2996e6a07b2d449bca",
    "7304006194f8530b9e19df1310a3670f",
    "cdad4692405c556ca63185bee512e95e",
    "c4682788c7e85d739ce043b3f6eaff70",
]


def get_memory_used_in_mb():
    return dict(psutil.virtual_memory()._asdict())["used"] / 1e6


def test_thumbnail_cache_no_additional_memory_usage_after_first_thumbnail_request():
    for slide_id in slide_ids:
        r = requests.get(f"http://localhost:8080/v1/slides/{slide_id}/thumbnail/max_size/500/500")
        assert r.status_code == 200
    memory_usage_after_first_thumbnail_request = get_memory_used_in_mb()
    for _ in range(5):
        for slide_id in slide_ids:
            r = requests.get(f"http://localhost:8080/v1/slides/{slide_id}/thumbnail/max_size/500/500")
            assert r.status_code == 200
    memory_usage_after_addtional_thumbnail_requests = get_memory_used_in_mb()
    assert (memory_usage_after_addtional_thumbnail_requests - memory_usage_after_first_thumbnail_request) < 10


def test_thumbnail_cache_speedup_test():
    time.sleep(6)  # make sure slide is closed
    start = time.time()
    r = requests.get(f"http://localhost:8080/v1/slides/f863c2ef155654b1af0387acc7ebdb60/thumbnail/max_size/500/500")
    time_first = time.time() - start
    assert r.status_code == 200
    start = time.time()
    r = requests.get(f"http://localhost:8080/v1/slides/f863c2ef155654b1af0387acc7ebdb60/thumbnail/max_size/500/500")
    time_second = time.time() - start
    assert r.status_code == 200
    speedup = time_first / time_second
    assert speedup > 4.0  # check speedup at least 4x, should usually be more like 10x
