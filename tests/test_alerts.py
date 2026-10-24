"""Alertas de ingesta: agrupación por equipo y problema, y sus endpoints."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from source.database.database import get_db
from source.main import app
from source.models.alert import Alert, AlertOccurrence
from source.models.device import Device, DeviceAssignment
from source.services.auth import get_current_user
from source.services.devices import provision_device


def _ingest(client, token, points):
    return client.post(
        "/devices/ingest",
        json={"batch_id": str(uuid4()), "points": points},
        headers={"Authorization": f"Bearer {token}"},
    )


def _no_assignment_point(sequence):
    before = datetime.now(UTC) - timedelta(minutes=5)
    return {
        "sequence": sequence,
        "lat": -31.4,
        "long": -64.2,
        "speed": 20,
        "heading": 90,
        "recorded_at": before.isoformat(),
    }


def _make_device_reject_no_assignment(db_session, test_truck, identifier):
    """Aprovisiona un equipo cuya asignación empieza mañana: todo punto cae en `no_assignment`."""
    token = provision_device(db_session, identifier, test_truck.id)
    device = db_session.query(Device).filter_by(identifier=identifier).one()
    assignment = db_session.query(DeviceAssignment).filter_by(device_id=device.id).one()
    assignment.valid_from = datetime.now(UTC) + timedelta(days=1)
    db_session.commit()
    return token


@pytest.fixture()
def member_client(db_session, test_user):
    """Sesión de un `member`: puede leer, no puede cerrar."""

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


def _add_open_alert(db_session, organization_id, identifier, problem_type):
    device = Device(
        identifier=identifier,
        token_hash=(identifier * 8)[:64].ljust(64, "0"),
        organization_id=organization_id,
    )
    db_session.add(device)
    db_session.commit()
    alert = Alert(
        organization_id=organization_id,
        device_id=device.id,
        problem_type=problem_type,
        status="open",
    )
    db_session.add(alert)
    db_session.commit()
    return alert


def test_rejections_group_into_a_single_open_alert(
    client, test_truck, test_org, db_session
):
    token = _make_device_reject_no_assignment(db_session, test_truck, "ALERT-01")

    first = _ingest(client, token, [_no_assignment_point(1)])
    second = _ingest(client, token, [_no_assignment_point(2)])

    assert first.json()["results"][0]["reason"] == "no_assignment"
    assert second.json()["results"][0]["reason"] == "no_assignment"
    alerts = db_session.query(Alert).all()
    assert len(alerts) == 1
    assert alerts[0].problem_type == "no_assignment"
    assert alerts[0].status == "open"
    assert alerts[0].organization_id == test_org.id
    assert len(alerts[0].occurrences) == 2
    assert db_session.query(AlertOccurrence).count() == 2


def test_different_problem_types_make_separate_alerts(client, test_truck, db_session):
    token = _make_device_reject_no_assignment(db_session, test_truck, "ALERT-02")

    _ingest(client, token, [_no_assignment_point(1)])
    _ingest(client, token, [["malformed"]])

    alerts = db_session.query(Alert).order_by(Alert.problem_type).all()
    assert {alert.problem_type for alert in alerts} == {"invalid_point", "no_assignment"}


def test_a_closed_alert_that_recurs_opens_a_linked_one(
    client, test_truck, db_session
):
    token = _make_device_reject_no_assignment(db_session, test_truck, "ALERT-03")

    _ingest(client, token, [_no_assignment_point(1)])
    closed = db_session.query(Alert).one()
    closed.status = "closed"
    closed.closed_at = datetime.now(UTC)
    db_session.commit()

    _ingest(client, token, [_no_assignment_point(2)])

    alerts = db_session.query(Alert).order_by(Alert.id).all()
    assert [alert.status for alert in alerts] == ["closed", "open"]
    assert alerts[1].previous_alert_id == closed.id


def test_admin_lists_open_alerts_with_occurrence_count(
    admin_client, db_session, test_org
):
    _add_open_alert(db_session, test_org.id, "ALERT-04", "invalid_point")

    response = admin_client.get("/alerts")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["problem_type"] == "invalid_point"
    assert body[0]["device"] == "ALERT-04"
    assert body[0]["occurrences"] == 0


def test_alerts_are_scoped_to_the_users_organization(
    admin_client, db_session, test_org, test_org2
):
    _add_open_alert(db_session, test_org.id, "ALERT-OWN", "no_truck")
    _add_open_alert(db_session, test_org2.id, "ALERT-FOREIGN", "no_truck")

    body = admin_client.get("/alerts").json()

    assert [alert["device"] for alert in body] == ["ALERT-OWN"]


def test_admin_closes_an_alert(admin_client, db_session, test_org):
    alert = _add_open_alert(db_session, test_org.id, "ALERT-05", "inactive_truck")

    response = admin_client.post(f"/alerts/{alert.id}/close")

    assert response.status_code == 200
    db_session.refresh(alert)
    assert alert.status == "closed"
    assert alert.closed_at is not None


def test_closing_an_already_closed_alert_is_rejected(
    admin_client, db_session, test_org
):
    alert = _add_open_alert(db_session, test_org.id, "ALERT-06", "no_truck")
    admin_client.post(f"/alerts/{alert.id}/close")

    assert admin_client.post(f"/alerts/{alert.id}/close").status_code == 400


def test_closing_a_foreign_alert_looks_like_a_missing_one(
    admin_client, db_session, test_org2
):
    alert = _add_open_alert(db_session, test_org2.id, "ALERT-07", "no_truck")

    assert admin_client.post(f"/alerts/{alert.id}/close").status_code == 404
    db_session.refresh(alert)
    assert alert.status == "open"


def test_a_member_can_read_but_not_close(member_client, db_session, test_org):
    alert = _add_open_alert(db_session, test_org.id, "ALERT-08", "no_truck")

    assert member_client.get("/alerts").status_code == 200
    assert member_client.post(f"/alerts/{alert.id}/close").status_code == 403
