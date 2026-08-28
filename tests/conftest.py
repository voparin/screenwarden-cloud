import os
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from cloud.db.models import Base
from cloud.db.session import get_db
import cloud.db.session as db_session_module
from cloud.api.app import create_app


@pytest.fixture(scope="function")
def db_engine():
    # Shared in-memory SQLite: one connection shared across all uses so the
    # same data is visible to both the test and the app under test.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    # Patch the module-level engine so app startup's create_tables() is a no-op
    # against the same in-memory DB rather than creating a separate file.
    original_engine = db_session_module.engine
    db_session_module.engine = engine
    yield engine
    db_session_module.engine = original_engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
