import os

# Provide required settings before importing the app so tests run without a .env
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef0123456789")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from source.database.database import Base, get_db
from source.main import app
from source.models.organization import Organization
from source.models.truck import Truck
from source.models.user import User
from source.services.auth import get_current_user, hash_password

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_current_user():
        return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def test_org(db_session):
    """Crea una organización de prueba con invitation_code conocido."""
    org = Organization(name="Test Org", invitation_code="TEST-CODE")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture()
def test_org2(db_session):
    """Crea una segunda organización de prueba para tests de aislamiento."""
    org = Organization(name="Test Org 2", invitation_code="TEST-CODE-2")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture()
def test_user(db_session, test_org):
    """Crea un usuario de prueba asignado a la organización de prueba."""
    from source.services.auth import hash_password
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password=hash_password("testpass123"),
        organization_id=test_org.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def test_truck(db_session, test_org):
    """Crea un camión de prueba asignado a la organización de prueba."""
    truck = Truck(id=1, plate="TEST123", organization_id=test_org.id)
    db_session.add(truck)
    db_session.commit()
    db_session.refresh(truck)
    return truck


@pytest.fixture()
def admin_user(db_session, test_org):
    """Crea un usuario administrador de prueba."""
    user = User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        hashed_password=hash_password("adminpass123"),
        organization_id=test_org.id,
        role="org_admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def platform_user(db_session, test_org):
    """Crea un usuario con rol de administrador de plataforma."""
    user = User(
        username="platform",
        email="platform@example.com",
        full_name="Platform Admin",
        hashed_password=hash_password("platformpass123"),
        organization_id=test_org.id,
        role="platform_admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def platform_client(db_session, platform_user):
    """Client con usuario administrador de plataforma autenticado."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_current_user():
        return platform_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_client(db_session, admin_user):
    """Client con usuario administrador autenticado (sobrescribe get_current_user)."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_current_user():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
