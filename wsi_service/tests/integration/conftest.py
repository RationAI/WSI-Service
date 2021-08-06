import time

import pytest
import requests


@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    for _ in range(60):
        try:
            r = requests.get("http://localhost:8080/alive")
            if r.json()["status"] == "ok":
                response = requests.get("http://localhost:8080/v1/refresh_local_mapper")
                assert response.status_code == 200
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
