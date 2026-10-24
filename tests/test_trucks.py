import pytest
from fastapi.testclient import TestClient

from source.database.database import get_db
from source.main import app
from source.services.auth import get_current_user


@pytest.fixture()
def trucks_client(db_session, test_org, test_user):
    """Client con usuario autenticado para tests de trucks."""

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


def test_get_trucks_empty(trucks_client):
    response = trucks_client.get("/trucks")
    assert response.status_code == 200
    assert response.json() == []


def test_add_truck_and_list(admin_client):
    response = admin_client.post(
        "/trucks",
        json={"id": 1, "plate": "ABC123"},
    )
    assert response.status_code == 200
    trucks = admin_client.get("/trucks").json()
    assert len(trucks) == 1
    assert trucks[0]["plate"] == "ABC123"


def test_duplicate_truck_returns_400(admin_client):
    payload = {"id": 1, "plate": "ABC123"}
    assert admin_client.post("/trucks", json=payload).status_code == 200
    assert admin_client.post("/trucks", json=payload).status_code == 400


def test_new_truck_has_no_location_until_its_device_reports(admin_client):
    """El alta no inyecta un punto: la primera ubicación la manda el dispositivo."""
    assert admin_client.post("/trucks", json={"id": 2, "plate": "XYZ789"}).status_code == 200

    response = admin_client.get("/trucks/2/location")

    assert response.status_code == 404
    assert admin_client.get("/trucks/2/iter").json() == []
