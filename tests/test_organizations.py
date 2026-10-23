from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from source.database.database import get_db
from source.main import app
from source.services.auth import get_current_user

REGISTER_PAYLOAD = {
    "username": "invitado",
    "email": "invitado@example.com",
    "full_name": "Usuario Invitado",
    "password": "SeguraABC1234",
}


@pytest.fixture()
def auth_client(db_session):
    """Client with real auth dependencies; only get_db is overridden."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def cliente_client(db_session, test_user):
    """Client authenticated as a regular (non-admin) user."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register(client, **overrides):
    return client.post("/auth/register", json={**REGISTER_PAYLOAD, **overrides})


# ---- creation and listing ----


def test_admin_creates_organization_with_generated_code(admin_client):
    response = admin_client.post("/organizations", json={"name": "Fletera Nueva"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Fletera Nueva"
    assert body["invitation_code"]
    assert body["invitation_expires_at"] is None
    assert body["invitation_revoked_at"] is None
    assert body["invitation_active"] is True


def test_admin_creates_organization_with_expiry(admin_client):
    response = admin_client.post(
        "/organizations", json={"name": "Fletera Temporal", "expires_in_days": 30}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["invitation_expires_at"] is not None
    assert body["invitation_active"] is True


def test_duplicate_organization_name_returns_400(admin_client, test_org):
    response = admin_client.post("/organizations", json={"name": test_org.name})
    assert response.status_code == 400
    assert response.json()["detail"] == "Ya existe una organización con ese nombre"


def test_client_cannot_create_organization(cliente_client):
    response = cliente_client.post("/organizations", json={"name": "Intrusa"})
    assert response.status_code == 403


def test_admin_lists_organizations(admin_client, test_org):
    response = admin_client.get("/organizations")
    assert response.status_code == 200
    ids = [org["id"] for org in response.json()]
    assert test_org.id in ids


def test_client_cannot_list_organizations(cliente_client):
    assert cliente_client.get("/organizations").status_code == 403


# ---- invitation inspection, rotation and revocation ----


def test_admin_reads_invitation(admin_client, test_org):
    response = admin_client.get(f"/organizations/{test_org.id}/invitation")
    assert response.status_code == 200
    body = response.json()
    assert body["invitation_code"] == test_org.invitation_code
    assert body["invitation_active"] is True


def test_unknown_organization_returns_404(admin_client):
    response = admin_client.get("/organizations/9999/invitation")
    assert response.status_code == 404
    assert response.json()["detail"] == "Organización no encontrada"


def test_rotate_generates_new_code_and_clears_revocation(admin_client, test_org, db_session):
    test_org.invitation_revoked_at = datetime.now(UTC)
    db_session.commit()
    previous_code = test_org.invitation_code

    response = admin_client.post(
        f"/organizations/{test_org.id}/invitation/rotate", json={"expires_in_days": 7}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["invitation_code"] != previous_code
    assert body["invitation_revoked_at"] is None
    assert body["invitation_expires_at"] is not None
    assert body["invitation_active"] is True


def test_rotate_without_expiry_clears_expiry(admin_client, test_org, db_session):
    test_org.invitation_expires_at = datetime.now(UTC) + timedelta(days=5)
    db_session.commit()

    response = admin_client.post(
        f"/organizations/{test_org.id}/invitation/rotate", json={}
    )
    assert response.status_code == 200
    assert response.json()["invitation_expires_at"] is None


def test_revoked_invitation_is_rejected_at_registration(admin_client, auth_client, test_org):
    response = admin_client.delete(f"/organizations/{test_org.id}/invitation")
    assert response.status_code == 200
    assert response.json()["invitation_active"] is False
    assert response.json()["invitation_revoked_at"] is not None

    rejected = register(auth_client, invitation_code=test_org.invitation_code)
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "Código de invitación inválido"


def test_expired_invitation_is_rejected_at_registration(db_session, auth_client, test_org):
    test_org.invitation_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    rejected = register(auth_client, invitation_code=test_org.invitation_code)
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "Código de invitación inválido"


def test_active_invitation_allows_registration(auth_client, test_org, db_session):
    response = register(auth_client, invitation_code=test_org.invitation_code)
    assert response.status_code == 201

    from source.models.user import User

    user = db_session.query(User).filter(User.username == "invitado").first()
    assert user is not None
    assert user.organization_id == test_org.id


def test_rotated_code_replaces_the_previous_one(admin_client, auth_client, test_org):
    previous_code = test_org.invitation_code
    rotated = admin_client.post(
        f"/organizations/{test_org.id}/invitation/rotate", json={}
    ).json()
    new_code = rotated["invitation_code"]
    assert new_code != previous_code

    old = register(auth_client, invitation_code=previous_code)
    assert old.status_code == 400

    fresh = register(
        auth_client,
        username="invitado2",
        email="invitado2@example.com",
        invitation_code=new_code,
    )
    assert fresh.status_code == 201
