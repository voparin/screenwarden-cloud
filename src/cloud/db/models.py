import uuid
from datetime import datetime, timezone, date
from sqlalchemy import (
    Column, String, Integer, Text, DateTime, Date, ForeignKey, UniqueConstraint, JSON
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _uuid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    def __init__(self, **kwargs):
        # Assign a UUID to 'id' immediately at instantiation if not provided,
        # so user.id is available before flush (e.g. to set FK on related rows).
        # SA wraps __init__ via _initialize_instance; do NOT call super().__init__
        # with kwargs — that resolves to object.__init__ which rejects them.
        # Set attributes directly; SA instrumentation fires via setattr.
        if "id" not in kwargs and hasattr(self.__class__, "id"):
            kwargs["id"] = _uuid()
        for key, value in kwargs.items():
            setattr(self, key, value)


class Family(Base):
    __tablename__ = "families"
    id = Column(String, primary_key=True, default=_uuid)
    email = Column(Text, nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    devices = relationship("Device", back_populates="family")


class Device(Base):
    __tablename__ = "devices"
    id = Column(String, primary_key=True, default=_uuid)
    family_id = Column(String, ForeignKey("families.id"), nullable=False)
    name = Column(Text, nullable=False)
    device_token = Column(Text, nullable=False, unique=True)
    last_seen_at = Column(DateTime, nullable=True)
    registered_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    family = relationship("Family", back_populates="devices")
    child_users = relationship("ChildUser", back_populates="device")


class ChildUser(Base):
    __tablename__ = "child_users"
    __table_args__ = (UniqueConstraint("device_id", "username"),)
    id = Column(String, primary_key=True, default=_uuid)
    device_id = Column(String, ForeignKey("devices.id"), nullable=False)
    username = Column(Text, nullable=False)
    device = relationship("Device", back_populates="child_users")
    usage_rows = relationship("DailyUsageMirror", back_populates="user")
    commands = relationship("Command", back_populates="user")
    config = relationship("ConfigMirror", back_populates="user", uselist=False)


class DailyUsageMirror(Base):
    __tablename__ = "daily_usage_mirror"
    __table_args__ = (UniqueConstraint("user_id", "date"),)
    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("child_users.id"), nullable=False)
    date = Column(Date, nullable=False)
    total_seconds = Column(Integer, nullable=False, default=0)
    synced_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user = relationship("ChildUser", back_populates="usage_rows")


class Command(Base):
    __tablename__ = "commands"
    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("child_users.id"), nullable=False)
    type = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    picked_up_at = Column(DateTime, nullable=True)
    user = relationship("ChildUser", back_populates="commands")


class ConfigMirror(Base):
    __tablename__ = "config_mirror"
    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("child_users.id"), nullable=False, unique=True)
    daily_limit_minutes = Column(Integer, nullable=False)
    warning_minutes = Column(Integer, nullable=False)
    grace_minutes = Column(Integer, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user = relationship("ChildUser", back_populates="config")


class PairingCode(Base):
    __tablename__ = "pairing_codes"
    code = Column(Text, primary_key=True)
    family_id = Column(String, ForeignKey("families.id"), nullable=True)
    device_token_pending = Column(Text, nullable=True)
    initiated_by = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
