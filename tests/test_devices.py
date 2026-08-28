import pytest


def signup_and_token(client, email="parent@test.com"):
    r = client.post("/auth/signup", json={"email": email, "password": "secret"})
    return r.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_list_devices_empty(client):
    token = signup_and_token(client)
    r = client.get("/devices", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json() == []


def test_parent_initiated_pairing_code(client):
    token = signup_and_token(client)
    r = client.post("/devices/pairing-code", headers=auth_headers(token))
    assert r.status_code == 201
    data = r.json()
    assert data["code"].startswith("SW-")
    assert len(data["code"]) == 9


def test_daemon_register_with_parent_code(client):
    token = signup_and_token(client)
    code_r = client.post("/devices/pairing-code", headers=auth_headers(token))
    code = code_r.json()["code"]
    r = client.post("/devices/register", json={"pairing_code": code, "device_name": "Test laptop"})
    assert r.status_code == 200
    assert "device_token" in r.json()


def test_daemon_register_nonexistent_code_returns_404(client):
    r = client.post("/devices/register", json={"pairing_code": "SW-ZZZZZZ", "device_name": "x"})
    assert r.status_code == 404


def test_list_devices_after_registration(client):
    token = signup_and_token(client)
    code = client.post("/devices/pairing-code", headers=auth_headers(token)).json()["code"]
    client.post("/devices/register", json={"pairing_code": code, "device_name": "Laptop"})
    r = client.get("/devices", headers=auth_headers(token))
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Laptop"
