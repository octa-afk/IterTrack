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


def test_add_truck_and_list(trucks_client):
    response = trucks_client.post(
        "/trucks",
        json={"truck": {"id": 1, "plate": "ABC123"}, "location": {"lat": -31.42, "long": -64.18}},
    )
    assert response.status_code == 200
    trucks = trucks_client.get("/trucks").json()
    assert len(trucks) == 1
    assert trucks[0]["plate"] == "ABC123"


def test_duplicate_truck_returns_400(trucks_client):
    payload = {"truck": {"id": 1, "plate": "ABC123"}, "location": {"lat": -31.42, "long": -64.18}}
    assert trucks_client.post("/trucks", json=payload).status_code == 200
    assert trucks_client.post("/trucks", json=payload).status_code == 400


def test_invalid_coordinates_rejected(trucks_client):
    response = trucks_client.post(
        "/trucks",
        json={"truck": {"id": 2, "plate": "XYZ789"}, "location": {"lat": 123, "long": -64.18}},
    )
    assert response.status_code == 422
