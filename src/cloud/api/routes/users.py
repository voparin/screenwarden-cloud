from datetime import date, datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from cloud.db.session import get_db
from cloud.db.models import ChildUser, DailyUsageMirror, Command, ConfigMirror, Device
from cloud.api.auth import get_current_family_id

router = APIRouter()


def get_user_for_family(user_id: str, family_id: str, db: Session) -> ChildUser:
    user = db.query(ChildUser).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    device = db.query(Device).filter_by(id=user.device_id, family_id=family_id).first()
    if not device:
        raise HTTPException(status_code=403, detail="Access denied")
    return user


@router.get("/{user_id}/today")
def get_today(
    user_id: str,
    family_id: str = Depends(get_current_family_id),
    db: Session = Depends(get_db),
):
    user = get_user_for_family(user_id, family_id, db)
    row = db.query(DailyUsageMirror).filter_by(user_id=user.id, date=date.today()).first()
    cfg = db.query(ConfigMirror).filter_by(user_id=user.id).first()
    total = row.total_seconds if row else 0
    limit_sec = (cfg.daily_limit_minutes * 60) if cfg else None
    return {
        "total_seconds": total,
        "daily_limit_minutes": cfg.daily_limit_minutes if cfg else None,
        "remaining_seconds": max(0, limit_sec - total) if limit_sec else None,
    }


@router.get("/{user_id}/history")
def get_history(
    user_id: str,
    family_id: str = Depends(get_current_family_id),
    db: Session = Depends(get_db),
):
    user = get_user_for_family(user_id, family_id, db)
    rows = (
        db.query(DailyUsageMirror)
        .filter_by(user_id=user.id)
        .order_by(DailyUsageMirror.date.desc())
        .limit(30)
        .all()
    )
    return [{"date": str(r.date), "total_seconds": r.total_seconds} for r in rows]


class GrantRequest(BaseModel):
    extra_minutes: int = Field(..., gt=0, description="Must be positive")
    reason: Optional[str] = None


@router.post("/{user_id}/grants", status_code=201)
def create_grant(
    user_id: str,
    body: GrantRequest,
    family_id: str = Depends(get_current_family_id),
    db: Session = Depends(get_db),
):
    user = get_user_for_family(user_id, family_id, db)
    cmd = Command(
        user_id=user.id,
        type="grant",
        payload={"extra_seconds": body.extra_minutes * 60, "reason": body.reason},
    )
    db.add(cmd)
    db.commit()
    return {"id": cmd.id, "extra_seconds": body.extra_minutes * 60}


class ConfigRequest(BaseModel):
    daily_limit_minutes: int = Field(..., gt=0)
    warning_minutes: int = Field(..., ge=0)
    grace_minutes: int = Field(..., ge=0)


@router.put("/{user_id}/config")
def update_config(
    user_id: str,
    body: ConfigRequest,
    family_id: str = Depends(get_current_family_id),
    db: Session = Depends(get_db),
):
    user = get_user_for_family(user_id, family_id, db)
    cfg = db.query(ConfigMirror).filter_by(user_id=user.id).first()
    if cfg:
        cfg.daily_limit_minutes = body.daily_limit_minutes
        cfg.warning_minutes = body.warning_minutes
        cfg.grace_minutes = body.grace_minutes
        cfg.updated_at = datetime.now(timezone.utc)
    else:
        cfg = ConfigMirror(
            user_id=user.id,
            daily_limit_minutes=body.daily_limit_minutes,
            warning_minutes=body.warning_minutes,
            grace_minutes=body.grace_minutes,
        )
        db.add(cfg)
    cmd = Command(
        user_id=user.id,
        type="config_change",
        payload={
            "daily_limit_minutes": body.daily_limit_minutes,
            "warning_minutes": body.warning_minutes,
            "grace_minutes": body.grace_minutes,
        },
    )
    db.add(cmd)
    db.commit()
    return {"daily_limit_minutes": cfg.daily_limit_minutes}
