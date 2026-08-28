import pytest
from datetime import date, datetime
from cloud.db.models import Device, ChildUser, DailyUsageMirror, Command, ConfigMirror, Family
from cloud.api.auth import generate_device_token, create_access_token


def setup_device(db_session):
    from cloud.db.models import Family
    family = Family(email="f@test.com", password_hash="x")
    db_session.add(family)
    db_session.flush()
    token = generate_device_token()
    device = Device(family_id=family.id, name="Laptop", device_token=token)
    db_session.add(device)
    db_session.commit()
    return device, token


def test_sync_creates_usage_mirror(client, db_session):
    device, token = setup_device(db_session)
    r = client.post(
        "/sync",
        json={"users": [{"username": "jakob", "date": "2026-08-28", "total_seconds": 3600, "last_sync_at": "2026-08-28T10:00:00Z"}]},
        headers={"X-Device-Token": token},
    )
    assert r.status_code == 200
    row = db_session.query(DailyUsageMirror).first()
    assert row.total_seconds == 3600


def test_sync_upserts_usage(client, db_session):
    device, token = setup_device(db_session)
    for seconds in [1800, 3600]:
        client.post(
            "/sync",
            json={"users": [{"username": "jakob", "date": "2026-08-28", "total_seconds": seconds, "last_sync_at": "2026-08-28T10:00:00Z"}]},
            headers={"X-Device-Token": token},
        )
    assert db_session.query(DailyUsageMirror).count() == 1
    db_session.expire_all()
    assert db_session.query(DailyUsageMirror).first().total_seconds == 3600


def test_sync_returns_pending_commands(client, db_session):
    device, token = setup_device(db_session)
    # First sync to register user
    client.post(
        "/sync",
        json={"users": [{"username": "jakob", "date": "2026-08-28", "total_seconds": 0, "last_sync_at": "2026-08-28T10:00:00Z"}]},
        headers={"X-Device-Token": token},
    )
    user = db_session.query(ChildUser).first()
    cmd = Command(user_id=user.id, type="grant", payload={"extra_seconds": 900})
    db_session.add(cmd)
    db_session.commit()

    r = client.post(
        "/sync",
        json={"users": [{"username": "jakob", "date": "2026-08-28", "total_seconds": 100, "last_sync_at": "2026-08-28T10:00:30Z"}]},
        headers={"X-Device-Token": token},
    )
    assert r.status_code == 200
    commands = r.json()["commands"]
    assert len(commands) == 1
    assert commands[0]["type"] == "grant"
    assert commands[0]["payload"]["extra_seconds"] == 900


def test_sync_marks_commands_picked_up(client, db_session):
    device, token = setup_device(db_session)
    client.post("/sync", json={"users": [{"username": "jakob", "date": "2026-08-28", "total_seconds": 0, "last_sync_at": "2026-08-28T10:00:00Z"}]}, headers={"X-Device-Token": token})
    user = db_session.query(ChildUser).first()
    cmd = Command(user_id=user.id, type="grant", payload={"extra_seconds": 300})
    db_session.add(cmd)
    db_session.commit()
    client.post("/sync", json={"users": [{"username": "jakob", "date": "2026-08-28", "total_seconds": 0, "last_sync_at": "2026-08-28T10:00:30Z"}]}, headers={"X-Device-Token": token})
    db_session.expire_all()
    assert db_session.query(Command).first().picked_up_at is not None


def test_sync_invalid_token_returns_401(client):
    r = client.post("/sync", json={"users": []}, headers={"X-Device-Token": "invalid"})
    assert r.status_code == 401


def test_sync_returns_config(client, db_session):
    device, token = setup_device(db_session)
    client.post("/sync", json={"users": [{"username": "jakob", "date": "2026-08-28", "total_seconds": 0, "last_sync_at": "2026-08-28T10:00:00Z"}]}, headers={"X-Device-Token": token})
    user = db_session.query(ChildUser).first()
    cfg = ConfigMirror(user_id=user.id, daily_limit_minutes=90, warning_minutes=5, grace_minutes=3)
    db_session.add(cfg)
    db_session.commit()
    r = client.post("/sync", json={"users": [{"username": "jakob", "date": "2026-08-28", "total_seconds": 0, "last_sync_at": "2026-08-28T10:01:00Z"}]}, headers={"X-Device-Token": token})
    assert r.json()["config"]["jakob"]["daily_limit_minutes"] == 90
