from wsi_service.tests.test_api_helpers import client


def test_alive(client):
    r = client.get(url="/alive")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
