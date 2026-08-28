from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from cloud.db.session import get_db
from cloud.db.models import Family
from cloud.api.auth import (
    hash_password, verify_password,
    create_access_token,
)

router = APIRouter()


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/signup", status_code=201)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    if db.query(Family).filter_by(email=body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    family = Family(email=body.email, password_hash=hash_password(body.password))
    db.add(family)
    db.commit()
    db.refresh(family)
    access_token = create_access_token({"sub": family.id, "type": "access"})
    refresh_token = create_access_token(
        {"sub": family.id, "type": "refresh"},
        expires_delta=timedelta(days=90),
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    family = db.query(Family).filter_by(email=body.email).first()
    if not family or not verify_password(body.password, family.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": family.id, "type": "access"})
    refresh_token = create_access_token(
        {"sub": family.id, "type": "refresh"},
        expires_delta=timedelta(days=90),
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh")
def refresh(body: RefreshRequest):
    from cloud.api.auth import decode_access_token
    payload = decode_access_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    access_token = create_access_token({"sub": payload["sub"], "type": "access"})
    return {"access_token": access_token, "token_type": "bearer"}
