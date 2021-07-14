import asyncio
import time
from random import randint, shuffle

import aiohttp
import pytest

slide_ids = [
    "4b0ec5e0ec5e5e05ae9e500857314f20",  # no label, no macro
    "f863c2ef155654b1af0387acc7ebdb60",
    "c801ce3d1de45f2996e6a07b2d449bca",  # no label
    "7304006194f8530b9e19df1310a3670f",
    "cdad4692405c556ca63185bee512e95e",  # no label
    "c4682788c7e85d739ce043b3f6eaff70",  # no label
]


async def fetch(client, url):
    async with client.get(url) as response:
        if "macro" not in url and "label" not in url:
            assert response.status == 200
        return await response.read()


@pytest.mark.skip(reason="stresstest skipped due to long runtime")
@pytest.mark.asyncio
async def test_stresstest(event_loop):
    event_loop.set_debug(True)
    for _ in range(10):
        urls = []
        for _ in range(100):
            for slide_id in slide_ids:
                x = randint(0, 100)
                y = randint(0, 100)
                urls += [
                    f"http://localhost:8080/v1/slides/{slide_id}/info",
                    f"http://localhost:8080/v1/slides/{slide_id}/thumbnail/max_size/200/200",
                    f"http://localhost:8080/v1/slides/{slide_id}/label/max_size/200/200",
                    f"http://localhost:8080/v1/slides/{slide_id}/macro/max_size/200/200",
                    f"http://localhost:8080/v1/slides/{slide_id}/region/level/0/start/0/0/size/200/200",
                    f"http://localhost:8080/v1/slides/{slide_id}/tile/level/0/tile/{x}/{y}",
                ]
        shuffle(urls)

        tasks = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                tasks.append(fetch(session, url))
            await asyncio.gather(*tasks)

        time.sleep(6)
