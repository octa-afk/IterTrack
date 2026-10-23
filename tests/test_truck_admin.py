import pytest
from fastapi.testclient import TestClient

from source.database.database import get_db
from source.main import app
from source.models.truck import TrackingPoint, Truck
from source.models.user import User
from source.services.auth import hash_password


def login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password})


@pytest.fixture()
def api_client(db_session):
    """TestClient con dependencia real de get_db; get_current_user usa JWT."""

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
def admin_user(db_session, test_org):
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
def client_user(db_session, test_org):
    user = User(
        username="cliente",
        email="cliente@example.com",
        full_name="Cliente User",
        hashed_password=hash_password("clientepass123"),
        organization_id=test_org.id,
        role="member",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def admin_token(api_client, admin_user):
    response = login(api_client, "admin", "adminpass123")
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture()
def client_token(api_client, client_user):
    response = login(api_client, "cliente", "clientepass123")
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture()
def platform_user(db_session, test_org):
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
def platform_token(api_client, platform_user):
    response = login(api_client, "platform", "platformpass123")
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_activate_truck(api_client, admin_token, test_truck, db_session):
    response = api_client.patch(
        f"/trucks/{test_truck.id}/activate",
        json={"active": False},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["active"] is False

    # Volver a activar para dejar limpio
    response = api_client.patch(
        f"/trucks/{test_truck.id}/activate",
        json={"active": True},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["active"] is True


def test_client_cannot_activate_truck(api_client, client_token, test_truck):
    response = api_client.patch(
        f"/trucks/{test_truck.id}/activate",
        json={"active": False},
        headers=auth_header(client_token),
    )
    assert response.status_code == 403


def test_platform_admin_can_reassign_truck(
    api_client, platform_token, test_org2, test_truck, db_session
):
    response = api_client.patch(
        f"/trucks/{test_truck.id}/organization",
        json={"organization_id": test_org2.id},
        headers=auth_header(platform_token),
    )
    assert response.status_code == 200
    assert response.json()["organization_id"] == test_org2.id

    # Devolver a la org original para no romper otros tests
    test_truck.organization_id = test_org2.id  # ya fue reasignado; dejar como está es fine


def test_org_admin_cannot_reassign_truck(api_client, admin_token, test_truck, test_org2):
    response = api_client.patch(
        f"/trucks/{test_truck.id}/organization",
        json={"organization_id": test_org2.id},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 403


def test_client_cannot_reassign_truck(api_client, client_token, test_truck, test_org2):
    response = api_client.patch(
        f"/trucks/{test_truck.id}/organization",
        json={"organization_id": test_org2.id},
        headers=auth_header(client_token),
    )
    assert response.status_code == 403


def test_admin_can_create_truck(api_client, admin_token):
    response = api_client.post(
        "/trucks",
        json={"truck": {"id": 99, "plate": "ADMIN99"}, "location": {"lat": -31.42, "long": -64.18}},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200


def test_client_cannot_create_truck(api_client, client_token):
    response = api_client.post(
        "/trucks",
        json={"truck": {"id": 98, "plate": "CLIENT98"}, "location": {"lat": -31.42, "long": -64.18}},
        headers=auth_header(client_token),
    )
    assert response.status_code == 403


def test_admin_can_delete_truck_iter(api_client, admin_token, test_truck, db_session):
    # Agregar un punto primero para que haya historial
    db_session.add(
        TrackingPoint(
            truck_id=test_truck.id,
            lat=-31.42,
            long=-64.18,
            speed=0,
            heading=0,
        )
    )
    db_session.commit()

    response = api_client.delete(
        f"/trucks/{test_truck.id}/iter",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 204

    puntos = (
        db_session.query(TrackingPoint)
        .filter(TrackingPoint.truck_id == test_truck.id)
        .all()
    )
    assert len(puntos) == 0


def test_client_cannot_delete_truck_iter(api_client, client_token, test_truck):
    response = api_client.delete(
        f"/trucks/{test_truck.id}/iter",
        headers=auth_header(client_token),
    )
    assert response.status_code == 403


def test_admin_cannot_touch_other_org_truck(api_client, admin_token, test_org2, db_session):
    """Admin de org A no puede modificar camión de org B."""
    truck_b = Truck(id=50, plate="ORGB50", organization_id=test_org2.id)
    db_session.add(truck_b)
    db_session.commit()

    response = api_client.patch(
        f"/trucks/{truck_b.id}/activate",
        json={"active": False},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 404

    response = api_client.patch(
        f"/trucks/{truck_b.id}/organization",
        json={"organization_id": test_org2.id},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 403


def test_inactive_truck_rejects_location_update(api_client, admin_token, test_org, db_session):
    truck_inactive = Truck(id=60, plate="INACT60", organization_id=test_org.id, active=False)
    db_session.add(truck_inactive)
    db_session.commit()

    response = api_client.put(
        f"/trucks/{truck_inactive.id}/location",
        json={"lat": -31.42, "long": -64.18, "speed": 0, "heading": 0},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 409


def test_history_retained_after_deactivate(api_client, admin_token, test_truck, db_session):
    # Agregar un punto de historial
    db_session.add(
        TrackingPoint(
            truck_id=test_truck.id,
            lat=-31.42,
            long=-64.18,
            speed=0,
            heading=0,
        )
    )
    db_session.commit()

    # Desactivar el camión
    response = api_client.patch(
        f"/trucks/{test_truck.id}/activate",
        json={"active": False},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    # El historial debe seguir existiendo
    puntos = (
        db_session.query(TrackingPoint)
        .filter(TrackingPoint.truck_id == test_truck.id)
        .all()
    )
    assert len(puntos) == 1
