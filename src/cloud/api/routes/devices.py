from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from cloud.db.session import get_db
from cloud.db.models import Device, PairingCode, ChildUser
from cloud.api.auth import get_current_family_id, generate_device_token, generate_pairing_code

router = APIRouter()


class RegisterRequest(BaseModel):
    pairing_code: str
    device_name: str


@router.get("")
def list_devices(
    family_id: str = Depends(get_current_family_id),
    db: Session = Depends(get_db),
):
    devices = db.query(Device).filter_by(family_id=family_id).all()
    return [
        {"id": d.id, "name": d.name, "last_seen_at": d.last_seen_at, "registered_at": d.registered_at}
        for d in devices
    ]


@router.post("/pairing-code", status_code=201)
def create_pairing_code(
    family_id: str = Depends(get_current_family_id),
    db: Session = Depends(get_db),
):
    code = generate_pairing_code()
    pending_token = generate_device_token()
    pairing = PairingCode(
        code=code,
        family_id=family_id,
        device_token_pending=pending_token,
        initiated_by="parent",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(pairing)
    db.commit()
    return {"code": code, "expires_in_seconds": 600}


@router.post("/register")
def register_device(body: RegisterRequest, db: Session = Depends(get_db)):
    pairing = db.query(PairingCode).filter_by(code=body.pairing_code).first()
    if not pairing:
        raise HTTPException(status_code=404, detail="Pairing code not found")
    if pairing.used_at is not None:
        raise HTTPException(status_code=410, detail="Pairing code already used")
    expires_at = pairing.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=410, detail="Pairing code expired")

    # Mark used atomically before creating device
    pairing.used_at = datetime.now(timezone.utc)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=410, detail="Pairing code already used")

    device_token = pairing.device_token_pending or generate_device_token()
    device = Device(
        family_id=pairing.family_id,
        name=body.device_name,
        device_token=device_token,
    )
    db.add(device)
    db.commit()
    return {"device_token": device_token}


@router.get("/{device_id}")
def get_device(
    device_id: str,
    family_id: str = Depends(get_current_family_id),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter_by(id=device_id, family_id=family_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"id": device.id, "name": device.name, "last_seen_at": device.last_seen_at}


@router.get("/{device_id}/users")
def list_device_users(
    device_id: str,
    family_id: str = Depends(get_current_family_id),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter_by(id=device_id, family_id=family_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return [{"id": u.id, "username": u.username} for u in device.child_users]


@router.delete("/{device_id}/token")
def revoke_device_token(
    device_id: str,
    family_id: str = Depends(get_current_family_id),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter_by(id=device_id, family_id=family_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.device_token = generate_device_token()
    db.commit()
    return {"revoked": True}
