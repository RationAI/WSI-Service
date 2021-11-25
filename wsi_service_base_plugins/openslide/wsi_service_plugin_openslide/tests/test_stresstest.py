import asyncio
import time
from random import randint, shuffle

import aiohttp
import pytest

slide_ids = [
    "f5f3a03b77fb5e0497b95eaff84e9a21",  # no label, no macro
    "8d32dba05a4558218880f06caf30d3ac",
    "1886900087965c9e845b39aebaa45ee6",  # no label
    "45707118e3b55f1b8e03e1f19feee916",
    "1666fd894d23529dbb8129f27c796e14",  # no label
    "a7a5a6840e625616b08e7bca6ee790ca",  # no label
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
