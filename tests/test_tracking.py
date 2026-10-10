import pytest
from fastapi.testclient import TestClient

from source.main import app
from source.database.database import Base, get_db
from source.services.auth import get_current_user
from source.models.organization import Organization
from source.models.user import User
from source.models.truck import Truck
from source.services.auth import hash_password


@pytest.fixture()
def tracking_client(db_session, test_org, test_user):
    """Client con usuario autenticado de la organización de prueba."""

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


@pytest.fixture()
def other_org(db_session):
    """Crea una segunda organización para tests de aislamiento."""
    org = Organization(name="Other Org", invitation_code="OTHER-CODE")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture()
def other_truck(db_session, other_org):
    """Crea un camión de la segunda organización."""
    truck = Truck(id=99, plate="OTHER99", organization_id=other_org.id)
    db_session.add(truck)
    db_session.commit()
    db_session.refresh(truck)
    return truck


def test_get_trucks_only_returns_own_org(tracking_client, test_truck):
    """GET /trucks solo devuelve camiones de la organización del usuario."""
    response = tracking_client.get("/trucks")
    assert response.status_code == 200
    trucks = response.json()
    assert len(trucks) == 1
    assert trucks[0]["plate"] == "TEST123"


def test_get_trucks_excludes_other_org(tracking_client, test_truck, other_truck):
    """GET /trucks NO devuelve camiones de otras organizaciones."""
    response = tracking_client.get("/trucks")
    assert response.status_code == 200
    trucks = response.json()
    plates = [t["plate"] for t in trucks]
    assert "TEST123" in plates
    assert "OTHER99" not in plates


def test_post_truck_assigns_organization(tracking_client, db_session, test_user):
    """POST /trucks asigna automáticamente la organización del usuario."""
    response = tracking_client.post(
        "/trucks",
        json={"truck": {"id": 2, "plate": "NEW123"}, "location": {"lat": -31.42, "long": -64.18}},
    )
    assert response.status_code == 200
    
    # Verificar que el camión tiene la organización correcta
    truck = db_session.query(Truck).filter(Truck.plate == "NEW123").first()
    assert truck is not None
    assert truck.organization_id == test_user.organization_id


def test_put_location_other_org_truck_returns_404(tracking_client, other_truck):
    """PUT /{truck_id}/location con camión de otra organización → 404."""
    response = tracking_client.put(
        f"/trucks/{other_truck.id}/location",
        json={"lat": -31.42, "long": -64.18},
    )
    assert response.status_code == 404


def test_get_location_other_org_truck_returns_404(tracking_client, other_truck):
    """GET /{truck_id}/location con camión de otra organización → 404."""
    response = tracking_client.get(f"/trucks/{other_truck.id}/location")
    assert response.status_code == 404


def test_get_iter_other_org_truck_returns_404(tracking_client, other_truck):
    """GET /{truck_id}/iter con camión de otra organización → 404."""
    response = tracking_client.get(f"/trucks/{other_truck.id}/iter")
    assert response.status_code == 404


def test_delete_iter_other_org_truck_returns_404(tracking_client, other_truck):
    """DELETE /{truck_id}/iter con camión de otra organización → 404."""
    response = tracking_client.delete(f"/trucks/{other_truck.id}/iter")
    assert response.status_code == 404


def test_get_truck_ids_only_returns_own_org(tracking_client, test_truck, other_truck):
    """GET /trucks/ids solo devuelve camiones de la organización del usuario."""
    response = tracking_client.get("/trucks/ids")
    assert response.status_code == 200
    trucks = response.json()
    plates = [t["plate"] for t in trucks]
    assert "TEST123" in plates
    assert "OTHER99" not in plates


def test_put_location_own_truck_succeeds(tracking_client, test_truck):
    """PUT /{truck_id}/location con camión de la organización del usuario → 200."""
    response = tracking_client.put(
        f"/trucks/{test_truck.id}/location",
        json={"lat": -31.42, "long": -64.18},
    )
    assert response.status_code == 200
    assert response.json()["mensaje"] == "Ubicación actualizada correctamente"
