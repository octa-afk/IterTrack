from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from source.database.database import get_db
from source.main import app
from source.models.device import Device, DeviceAssignment
from source.models.truck import Truck
from source.services.auth import get_current_user


def ingest_payload():
    return {
        "batch_id": str(uuid4()),
        "points": [
            {
                "sequence": 1,
                "lat": -31.4,
                "long": -64.2,
                "speed": 20,
                "heading": 90,
                "recorded_at": datetime.now(UTC).isoformat(),
            }
        ],
    }


def open_assignment_for_device(db_session, device_id):
    return (
        db_session.query(DeviceAssignment)
        .filter(DeviceAssignment.device_id == device_id, DeviceAssignment.valid_to.is_(None))
        .first()
    )


@pytest.fixture()
def other_truck(db_session, test_org):
    truck = Truck(id=2, plate="TEST456", organization_id=test_org.id)
    db_session.add(truck)
    db_session.commit()
    db_session.refresh(truck)
    return truck


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


# ---- provisioning ----


def test_admin_provisions_device_and_receives_token(admin_client, test_truck, db_session):
    response = admin_client.post(
        "/devices", json={"identifier": "AA:BB:CC:DD:EE:01", "truck_id": test_truck.id}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["identifier"] == "AA:BB:CC:DD:EE:01"
    assert body["token"]
    assert body["active"] is True
    assert body["assignment"]["truck_id"] == test_truck.id
    assert "token_hash" not in body

    device = db_session.query(Device).filter_by(identifier="AA:BB:CC:DD:EE:01").one()
    assert device.token_hash != body["token"]
    assert open_assignment_for_device(db_session, device.id) is not None


def test_duplicate_identifier_returns_400(admin_client, test_truck):
    payload = {"identifier": "AA:BB:CC:DD:EE:02", "truck_id": test_truck.id}
    assert admin_client.post("/devices", json=payload).status_code == 201

    response = admin_client.post("/devices", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Ya existe un dispositivo con ese identificador"


def test_unknown_truck_returns_404(admin_client):
    response = admin_client.post("/devices", json={"identifier": "AA:BB:CC:DD:EE:03", "truck_id": 999})
    assert response.status_code == 404
    assert response.json()["detail"] == "Camión no encontrado"


def test_inactive_truck_returns_400(admin_client, test_truck, db_session):
    test_truck.active = False
    db_session.commit()

    response = admin_client.post(
        "/devices", json={"identifier": "AA:BB:CC:DD:EE:04", "truck_id": test_truck.id}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "El camión está inactivo"


def test_truck_with_open_assignment_returns_400(admin_client, test_truck):
    admin_client.post("/devices", json={"identifier": "AA:BB:CC:DD:EE:05", "truck_id": test_truck.id})

    response = admin_client.post(
        "/devices", json={"identifier": "AA:BB:CC:DD:EE:06", "truck_id": test_truck.id}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "El camión ya tiene un dispositivo asignado"


# ---- listing ----


def test_list_devices_includes_open_assignment(admin_client, test_truck):
    admin_client.post("/devices", json={"identifier": "AA:BB:CC:DD:EE:07", "truck_id": test_truck.id})

    response = admin_client.get("/devices")
    assert response.status_code == 200
    devices = response.json()
    assert len(devices) == 1
    assert devices[0]["assignment"]["truck_id"] == test_truck.id
    assert "token" not in devices[0]
    assert "token_hash" not in devices[0]


# ---- reassignment ----


def test_reassign_closes_previous_assignment_and_opens_new_one(
    admin_client, test_truck, other_truck, db_session
):
    created = admin_client.post(
        "/devices", json={"identifier": "AA:BB:CC:DD:EE:08", "truck_id": test_truck.id}
    ).json()
    device_id = created["id"]

    response = admin_client.post(f"/devices/{device_id}/reassign", json={"truck_id": other_truck.id})
    assert response.status_code == 200
    assert response.json()["assignment"]["truck_id"] == other_truck.id

    assignments = (
        db_session.query(DeviceAssignment)
        .filter(DeviceAssignment.device_id == device_id)
        .order_by(DeviceAssignment.id)
        .all()
    )
    assert len(assignments) == 2
    assert assignments[0].valid_to is not None
    assert assignments[1].valid_to is None
    assert assignments[1].truck_id == other_truck.id


def test_reassign_to_same_truck_returns_400(admin_client, test_truck):
    created = admin_client.post(
        "/devices", json={"identifier": "AA:BB:CC:DD:EE:09", "truck_id": test_truck.id}
    ).json()

    response = admin_client.post(
        f"/devices/{created['id']}/reassign", json={"truck_id": test_truck.id}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "El dispositivo ya está asignado a ese camión"


def test_reassign_to_occupied_truck_returns_400(admin_client, test_truck, other_truck):
    first = admin_client.post(
        "/devices", json={"identifier": "AA:BB:CC:DD:EE:0A", "truck_id": test_truck.id}
    ).json()
    admin_client.post(
        "/devices", json={"identifier": "AA:BB:CC:DD:EE:0B", "truck_id": other_truck.id}
    )

    response = admin_client.post(f"/devices/{first['id']}/reassign", json={"truck_id": other_truck.id})
    assert response.status_code == 400
    assert response.json()["detail"] == "El camión ya tiene un dispositivo asignado"


def test_unknown_device_returns_404(admin_client, test_truck):
    response = admin_client.post("/devices/9999/reassign", json={"truck_id": test_truck.id})
    assert response.status_code == 404
    assert response.json()["detail"] == "Dispositivo no encontrado"


# ---- token rotation and revocation ----


def test_rotate_invalidates_previous_token(admin_client, test_truck):
    created = admin_client.post(
        "/devices", json={"identifier": "AA:BB:CC:DD:EE:0C", "truck_id": test_truck.id}
    ).json()
    old_token = created["token"]

    rotated = admin_client.post(f"/devices/{created['id']}/token/rotate")
    assert rotated.status_code == 200
    new_token = rotated.json()["token"]
    assert new_token and new_token != old_token

    stale = admin_client.post(
        "/devices/ingest", json=ingest_payload(), headers={"Authorization": f"Bearer {old_token}"}
    )
    assert stale.status_code == 401

    fresh = admin_client.post(
        "/devices/ingest", json=ingest_payload(), headers={"Authorization": f"Bearer {new_token}"}
    )
    assert fresh.status_code == 200


def test_revoke_deactivates_device_and_frees_truck(admin_client, test_truck, db_session):
    created = admin_client.post(
        "/devices", json={"identifier": "AA:BB:CC:DD:EE:0D", "truck_id": test_truck.id}
    ).json()

    response = admin_client.post(f"/devices/{created['id']}/revoke")
    assert response.status_code == 200
    assert response.json()["active"] is False
    assert response.json()["assignment"] is None

    device = db_session.get(Device, created["id"])
    assert device is not None
    assert device.active is False
    assert open_assignment_for_device(db_session, created["id"]) is None

    rejected = admin_client.post(
        "/devices/ingest",
        json=ingest_payload(),
        headers={"Authorization": f"Bearer {created['token']}"},
    )
    assert rejected.status_code == 401

    replacement = admin_client.post(
        "/devices", json={"identifier": "AA:BB:CC:DD:EE:0E", "truck_id": test_truck.id}
    )
    assert replacement.status_code == 201


# ---- authorization ----


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/devices", None),
        ("post", "/devices", {"identifier": "AA:BB:CC:DD:EE:0F", "truck_id": 1}),
        ("post", "/devices/1/reassign", {"truck_id": 1}),
        ("post", "/devices/1/token/rotate", None),
        ("post", "/devices/1/revoke", None),
    ],
)
def test_client_cannot_manage_devices(cliente_client, method, path, body):
    response = cliente_client.request(method, path, json=body)
    assert response.status_code == 403
    assert response.json()["detail"].startswith("Se requiere rol de administrador")
