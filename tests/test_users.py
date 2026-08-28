import pytest
from datetime import date, datetime
from cloud.db.models import Family, Device, ChildUser, DailyUsageMirror, Command, ConfigMirror
from cloud.api.auth import generate_device_token, create_access_token


def make_family_device_user(db_session):
    family = Family(email="p@test.com", password_hash="x")
    db_session.add(family)
    db_session.flush()
    device = Device(family_id=family.id, name="Laptop", device_token=generate_device_token())
    db_session.add(device)
    db_session.flush()
    user = ChildUser(device_id=device.id, username="jakob")
    db_session.add(user)
    cfg = ConfigMirror(user_id=user.id, daily_limit_minutes=120, warning_minutes=5, grace_minutes=5)
    db_session.add(cfg)
    db_session.commit()
    token = create_access_token({"sub": family.id, "type": "access"})
    return user, token


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_today_returns_usage(client, db_session):
    user, token = make_family_device_user(db_session)
    db_session.add(DailyUsageMirror(user_id=user.id, date=date.today(), total_seconds=3600))
    db_session.commit()
    r = client.get(f"/users/{user.id}/today", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["total_seconds"] == 3600
    assert r.json()["daily_limit_minutes"] == 120


def test_today_returns_zero_if_no_row(client, db_session):
    user, token = make_family_device_user(db_session)
    r = client.get(f"/users/{user.id}/today", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["total_seconds"] == 0


def test_history_returns_rows(client, db_session):
    user, token = make_family_device_user(db_session)
    db_session.add(DailyUsageMirror(user_id=user.id, date=date(2026, 8, 27), total_seconds=1800))
    db_session.add(DailyUsageMirror(user_id=user.id, date=date(2026, 8, 28), total_seconds=3600))
    db_session.commit()
    r = client.get(f"/users/{user.id}/history", headers=auth(token))
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_grant_creates_command(client, db_session):
    user, token = make_family_device_user(db_session)
    r = client.post(f"/users/{user.id}/grants", json={"extra_minutes": 15, "reason": "done"}, headers=auth(token))
    assert r.status_code == 201
    cmd = db_session.query(Command).first()
    assert cmd.type == "grant"
    assert cmd.payload["extra_seconds"] == 900


def test_config_update_creates_command_and_updates_mirror(client, db_session):
    user, token = make_family_device_user(db_session)
    r = client.put(f"/users/{user.id}/config", json={"daily_limit_minutes": 60, "warning_minutes": 10, "grace_minutes": 3}, headers=auth(token))
    assert r.status_code == 200
    db_session.expire_all()
    cfg = db_session.query(ConfigMirror).filter_by(user_id=user.id).first()
    assert cfg.daily_limit_minutes == 60
    cmd = db_session.query(Command).filter_by(type="config_change").first()
    assert cmd.payload["daily_limit_minutes"] == 60
