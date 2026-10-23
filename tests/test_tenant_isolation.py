"""Aislamiento entre organizaciones y matriz de permisos de los tres roles.

Cubre el bloque 1 de `odd/tasks/demo-deployment.md`: un administrador de
organización solo puede operar sobre la suya, y el administrador de plataforma
puede leer todas pero solo escribe en el alta (onboarding).
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from source.database.database import get_db
from source.main import app
from source.models.device import Device, DeviceAssignment
from source.models.truck import Truck
from source.models.user import User
from source.services.auth import get_current_user, hash_password


@pytest.fixture()
def client_as(db_session):
    """Return a TestClient authenticated as the given user object."""

    def _client(user):
        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        def override_current_user():
            return user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_current_user
        return TestClient(app)

    yield _client
    app.dependency_overrides.clear()


def make_user(db_session, organization, username, role):
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username,
        hashed_password=hash_password("pass12345"),
        organization_id=organization.id,
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def make_device(db_session, organization, identifier):
    device = Device(
        identifier=identifier,
        token_hash=uuid4().hex,
        organization_id=organization.id,
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


def truck_payload(truck_id, plate):
    return {
        "truck": {"id": truck_id, "plate": plate},
        "location": {"lat": -31.42, "long": -64.18, "speed": 0, "heading": 0},
    }


# ---- organizations ----


def test_org_admin_lists_only_its_own_organization(client_as, db_session, test_org, test_org2):
    admin = make_user(db_session, test_org, "orgadmin1", "org_admin")

    with client_as(admin) as client:
        response = client.get("/organizations")

    assert response.status_code == 200
    assert [organization["id"] for organization in response.json()] == [test_org.id]


def test_platform_admin_lists_every_organization(client_as, db_session, test_org, test_org2):
    owner = make_user(db_session, test_org, "platform1", "platform_admin")

    with client_as(owner) as client:
        response = client.get("/organizations")

    assert response.status_code == 200
    assert {organization["id"] for organization in response.json()} == {test_org.id, test_org2.id}


def test_member_cannot_list_organizations(client_as, db_session, test_org):
    member = make_user(db_session, test_org, "member1", "member")

    with client_as(member) as client:
        response = client.get("/organizations")

    assert response.status_code == 403


def test_org_admin_cannot_read_another_organization_invitation(
    client_as, db_session, test_org, test_org2
):
    admin = make_user(db_session, test_org, "orgadmin2", "org_admin")

    with client_as(admin) as client:
        response = client.get(f"/organizations/{test_org2.id}/invitation")

    assert response.status_code == 404


def test_org_admin_cannot_rotate_another_organization_invitation(
    client_as, db_session, test_org, test_org2
):
    admin = make_user(db_session, test_org, "orgadmin3", "org_admin")

    with client_as(admin) as client:
        response = client.post(f"/organizations/{test_org2.id}/invitation/rotate", json={})

    assert response.status_code == 404


def test_org_admin_cannot_create_organization(client_as, db_session, test_org):
    admin = make_user(db_session, test_org, "orgadmin4", "org_admin")

    with client_as(admin) as client:
        response = client.post("/organizations", json={"name": "Nueva"})

    assert response.status_code == 403


def test_platform_admin_can_create_organization(client_as, db_session, test_org):
    owner = make_user(db_session, test_org, "platform2", "platform_admin")

    with client_as(owner) as client:
        response = client.post("/organizations", json={"name": "Nueva"})

    assert response.status_code == 201


# ---- truck onboarding ----


def test_platform_admin_creates_truck_in_target_organization(
    client_as, db_session, test_org, test_org2
):
    owner = make_user(db_session, test_org, "platform3", "platform_admin")

    with client_as(owner) as client:
        response = client.post(
            f"/organizations/{test_org2.id}/trucks", json=truck_payload(901, "PLAT901")
        )

    assert response.status_code == 200
    truck = db_session.get(Truck, 901)
    assert truck is not None
    assert truck.organization_id == test_org2.id


def test_org_admin_cannot_use_platform_onboarding_endpoint(
    client_as, db_session, test_org, test_org2
):
    admin = make_user(db_session, test_org, "orgadmin5", "org_admin")

    with client_as(admin) as client:
        response = client.post(
            f"/organizations/{test_org2.id}/trucks", json=truck_payload(902, "PLAT902")
        )

    assert response.status_code == 403
    assert db_session.get(Truck, 902) is None


def test_platform_admin_onboarding_rejects_unknown_organization(
    client_as, db_session, test_org
):
    owner = make_user(db_session, test_org, "platform4", "platform_admin")

    with client_as(owner) as client:
        response = client.post("/organizations/9999/trucks", json=truck_payload(903, "PLAT903"))

    assert response.status_code == 404


# ---- devices ----


def test_org_admin_lists_only_its_own_devices(client_as, db_session, test_org, test_org2):
    admin = make_user(db_session, test_org, "orgadmin6", "org_admin")
    own = make_device(db_session, test_org, "DEV-OWN")
    make_device(db_session, test_org2, "DEV-FOREIGN")

    with client_as(admin) as client:
        response = client.get("/devices")

    assert response.status_code == 200
    assert [device["id"] for device in response.json()] == [own.id]


def test_platform_admin_lists_every_device(client_as, db_session, test_org, test_org2):
    owner = make_user(db_session, test_org, "platform5", "platform_admin")
    make_device(db_session, test_org, "DEV-A")
    make_device(db_session, test_org2, "DEV-B")

    with client_as(owner) as client:
        response = client.get("/devices")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_org_admin_cannot_revoke_another_organization_device(
    client_as, db_session, test_org, test_org2
):
    admin = make_user(db_session, test_org, "orgadmin7", "org_admin")
    foreign = make_device(db_session, test_org2, "DEV-FOREIGN-2")

    with client_as(admin) as client:
        response = client.post(f"/devices/{foreign.id}/revoke")

    assert response.status_code == 404
    db_session.refresh(foreign)
    assert foreign.active is True


def test_org_admin_cannot_reassign_device_to_another_organization_truck(
    client_as, db_session, test_org, test_org2
):
    admin = make_user(db_session, test_org, "orgadmin8", "org_admin")
    device = make_device(db_session, test_org, "DEV-OWN-2")
    foreign_truck = Truck(id=910, plate="FOREIGN910", organization_id=test_org2.id)
    db_session.add(foreign_truck)
    db_session.commit()

    with client_as(admin) as client:
        response = client.post(f"/devices/{device.id}/reassign", json={"truck_id": 910})

    assert response.status_code in (400, 403, 404)
    assert (
        db_session.query(DeviceAssignment).filter(DeviceAssignment.device_id == device.id).count()
        == 0
    )


def test_org_admin_cannot_move_truck_to_another_organization(
    client_as, db_session, test_org, test_org2, test_truck
):
    admin = make_user(db_session, test_org, "orgadmin9", "org_admin")

    with client_as(admin) as client:
        response = client.patch(
            f"/trucks/{test_truck.id}/organization", json={"organization_id": test_org2.id}
        )

    assert response.status_code == 403
    db_session.refresh(test_truck)
    assert test_truck.organization_id == test_org.id


def test_truck_transfer_moves_assigned_device_to_the_new_organization(
    client_as, db_session, test_org, test_org2, test_truck
):
    owner = make_user(db_session, test_org, "platform6", "platform_admin")
    device = make_device(db_session, test_org, "DEV-TRANSFER")
    db_session.add(DeviceAssignment(device_id=device.id, truck_id=test_truck.id))
    db_session.commit()

    with client_as(owner) as client:
        response = client.patch(
            f"/trucks/{test_truck.id}/organization", json={"organization_id": test_org2.id}
        )

    assert response.status_code == 200
    db_session.refresh(device)
    assert device.organization_id == test_org2.id

    previous_tenant_admin = make_user(db_session, test_org, "orgadmin10", "org_admin")
    with client_as(previous_tenant_admin) as client:
        assert client.post(f"/devices/{device.id}/revoke").status_code == 404

    new_tenant_admin = make_user(db_session, test_org2, "orgadmin11", "org_admin")
    with client_as(new_tenant_admin) as client:
        listed = client.get("/devices")

    assert [entry["id"] for entry in listed.json()] == [device.id]
