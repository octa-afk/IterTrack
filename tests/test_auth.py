import pytest
from fastapi.testclient import TestClient

from source.database.database import get_db
from source.main import app
from source.models.organization import Organization

REGISTER_PAYLOAD = {
    "username": "chofer1",
    "email": "chofer1@example.com",
    "full_name": "Chofer Uno",
    "password": "SeguraABC1234",
    "invitation_code": "TEST-CODE",
}


@pytest.fixture()
def auth_client(db_session, test_org):
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


def register(client, payload=REGISTER_PAYLOAD):
    return client.post("/auth/register", json=payload)


def login(client, username="chofer1", password="SeguraABC1234"):
    return client.post("/auth/login", data={"username": username, "password": password})


def test_register_returns_201_without_password(auth_client):
    response = register(auth_client)
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "chofer1"
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_invalid_invitation_code_returns_400(auth_client):
    response = register(auth_client, {**REGISTER_PAYLOAD, "invitation_code": "WRONG-CODE"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Código de invitación inválido"


def test_register_valid_invitation_code_assigns_organization(auth_client, db_session):
    response = register(auth_client)
    assert response.status_code == 201

    # Verificar que el usuario quedó asignado a la organización correcta
    from source.models.user import User
    user = db_session.query(User).filter(User.username == "chofer1").first()
    assert user is not None
    assert user.organization_id is not None

    org = db_session.query(Organization).filter(Organization.id == user.organization_id).first()
    assert org is not None
    assert org.invitation_code == "TEST-CODE"


def test_register_duplicate_username_returns_400(auth_client):
    register(auth_client)
    response = register(auth_client, {**REGISTER_PAYLOAD, "email": "otro@example.com"})
    assert response.status_code == 400
    assert response.json()["detail"] == "El usuario ya existe"


def test_register_duplicate_email_returns_400(auth_client):
    register(auth_client)
    response = register(auth_client, {**REGISTER_PAYLOAD, "username": "otro"})
    assert response.status_code == 400
    assert response.json()["detail"] == "El email ya está registrado"


def test_register_invalid_email_returns_422(auth_client):
    response = register(auth_client, {**REGISTER_PAYLOAD, "email": "no-es-email"})
    assert response.status_code == 422


def test_register_rejects_password_shorter_than_eight_characters(auth_client):
    response = register(auth_client, {**REGISTER_PAYLOAD, "password": "Abc123!"})
    assert response.status_code == 422


def test_register_rejects_password_with_letters_only(auth_client):
    response = register(auth_client, {**REGISTER_PAYLOAD, "password": "abcdefghijkl"})
    assert response.status_code == 422


def test_register_rejects_password_with_numbers_only(auth_client):
    response = register(auth_client, {**REGISTER_PAYLOAD, "password": "123456789012"})
    assert response.status_code == 422


def test_register_accepts_valid_password(auth_client):
    response = register(auth_client, {**REGISTER_PAYLOAD, "password": "SeguraABC1234"})
    assert response.status_code == 201


def test_login_returns_token(auth_client):
    register(auth_client)
    response = login(auth_client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_returns_401(auth_client):
    register(auth_client)
    response = login(auth_client, password="incorrecta")
    assert response.status_code == 401
    assert response.json()["detail"] == "Usuario o contraseña incorrectos"


def test_me_with_valid_token_returns_user(auth_client):
    register(auth_client)
    token = login(auth_client).json()["access_token"]
    response = auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "chofer1"


def test_me_without_token_returns_401(auth_client):
    response = auth_client.get("/auth/me")
    assert response.status_code == 401


def test_me_with_random_token_returns_401(auth_client):
    response = auth_client.get(
        "/auth/me",
        headers={"Authorization": "Bearer random-invalid-token"},
    )
    assert response.status_code == 401


def test_protected_endpoint_without_token_returns_401(auth_client):
    response = auth_client.post(
        "/trucks",
        json={"truck": {"id": 1, "plate": "ABC123"}, "location": {"lat": -31.42, "long": -64.18}},
    )
    assert response.status_code == 401


def test_register_with_org_name_and_no_code_returns_400(auth_client, db_session):
    payload = {**REGISTER_PAYLOAD, "org_name": "Mi Empresa"}
    del payload["invitation_code"]
    response = register(auth_client, payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Debe proporcionar un código de invitación"

    # `org_name` must no longer create organizations.
    assert db_session.query(Organization).filter(Organization.name == "Mi Empresa").first() is None


def test_register_without_invitation_code_returns_400(auth_client):
    payload = {**REGISTER_PAYLOAD}
    del payload["invitation_code"]
    response = register(auth_client, payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Debe proporcionar un código de invitación"


def test_register_ignores_org_name_when_code_is_valid(auth_client, db_session, test_org):
    payload = {**REGISTER_PAYLOAD, "org_name": "Mi Empresa"}
    response = register(auth_client, payload)
    assert response.status_code == 201

    from source.models.user import User

    user = db_session.query(User).filter(User.username == "chofer1").first()
    assert user is not None
    assert user.organization_id == test_org.id
    assert db_session.query(Organization).filter(Organization.name == "Mi Empresa").first() is None


def test_register_org_isolation(auth_client, db_session, test_org, test_org2):
    """Verifica que registrarse con el código de una org no asigna a la otra."""
    payload = {
        **REGISTER_PAYLOAD,
        "username": "chofer2",
        "email": "chofer2@example.com",
        "invitation_code": "TEST-CODE-2",
    }
    response = register(auth_client, payload)
    assert response.status_code == 201

    from source.models.user import User
    user = db_session.query(User).filter(User.username == "chofer2").first()
    assert user is not None
    assert user.organization_id == test_org2.id
    assert user.organization_id != test_org.id
