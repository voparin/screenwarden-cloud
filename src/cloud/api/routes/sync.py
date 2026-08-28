from datetime import datetime, date as date_type
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from cloud.db.session import get_db
from cloud.db.models import Device, ChildUser, DailyUsageMirror, Command, ConfigMirror

router = APIRouter()


class UserSyncEntry(BaseModel):
    username: str
    date: str
    total_seconds: int
    last_sync_at: str


class SyncRequest(BaseModel):
    users: List[UserSyncEntry]


def get_device_from_token(
    x_device_token: str = Header(...),
    db: Session = Depends(get_db),
) -> Device:
    device = db.query(Device).filter_by(device_token=x_device_token).first()
    if not device:
        raise HTTPException(status_code=401, detail="Invalid device token")
    device.last_seen_at = datetime.utcnow()
    db.commit()
    return device


@router.post("/sync")
def sync(
    body: SyncRequest,
    device: Device = Depends(get_device_from_token),
    db: Session = Depends(get_db),
):
    commands_out = []
    config_out = {}

    for entry in body.users:
        user = db.query(ChildUser).filter_by(device_id=device.id, username=entry.username).first()
        if not user:
            user = ChildUser(device_id=device.id, username=entry.username)
            db.add(user)
            db.flush()

        # Parse date with error handling
        try:
            entry_date = date_type.fromisoformat(entry.date)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid date format: {entry.date}")

        # Upsert daily usage mirror
        usage = db.query(DailyUsageMirror).filter_by(
            user_id=user.id, date=entry_date
        ).first()
        if usage:
            usage.total_seconds = entry.total_seconds
            usage.synced_at = datetime.utcnow()
        else:
            usage = DailyUsageMirror(
                user_id=user.id,
                date=entry_date,
                total_seconds=entry.total_seconds,
            )
            db.add(usage)

        # Collect pending commands (not yet picked up)
        pending = db.query(Command).filter_by(user_id=user.id, picked_up_at=None).all()
        for cmd in pending:
            commands_out.append({
                "id": cmd.id,
                "username": entry.username,
                "type": cmd.type,
                "payload": cmd.payload,
            })
            cmd.picked_up_at = datetime.utcnow()

        # Collect config
        cfg = db.query(ConfigMirror).filter_by(user_id=user.id).first()
        if cfg:
            config_out[entry.username] = {
                "daily_limit_minutes": cfg.daily_limit_minutes,
                "warning_minutes": cfg.warning_minutes,
                "grace_minutes": cfg.grace_minutes,
            }

    db.commit()
    return {"commands": commands_out, "config": config_out}
