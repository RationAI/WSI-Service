import time

import pytest
import requests


@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    for _ in range(60):
        try:
            r = requests.get("http://localhost:8080/alive")
            if r.json()["status"] == "ok":
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
