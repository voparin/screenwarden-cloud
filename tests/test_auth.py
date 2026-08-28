import pytest


def test_signup_creates_family(client):
    r = client.post("/auth/signup", json={"email": "parent@test.com", "password": "secret123"})
    assert r.status_code == 201
    assert "access_token" in r.json()


def test_signup_duplicate_email_returns_409(client):
    client.post("/auth/signup", json={"email": "dup@test.com", "password": "secret123"})
    r = client.post("/auth/signup", json={"email": "dup@test.com", "password": "secret123"})
    assert r.status_code == 409


def test_login_returns_token(client):
    client.post("/auth/signup", json={"email": "login@test.com", "password": "secret123"})
    r = client.post("/auth/login", json={"email": "login@test.com", "password": "secret123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password_returns_401(client):
    client.post("/auth/signup", json={"email": "bad@test.com", "password": "secret123"})
    r = client.post("/auth/login", json={"email": "bad@test.com", "password": "wrong"})
    assert r.status_code == 401


def test_refresh_returns_new_token(client):
    r = client.post("/auth/signup", json={"email": "refresh@test.com", "password": "secret123"})
    refresh_token = r.json()["refresh_token"]
    r2 = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r2.status_code == 200
    assert "access_token" in r2.json()
