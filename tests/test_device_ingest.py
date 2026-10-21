from datetime import datetime, timedelta, timezone
from uuid import uuid4

from source.models.device import Device, DeviceAssignment
from source.models.ingestion import IngestedPoint, RejectedIngestPoint
from source.models.truck import TrackingPoint, Truck
from source.services.devices import hash_device_token, provision_device
from source.schemas.ingestion import DeviceIngestBatch, DeviceIngestPoint


def payload(batch_id=None, points=None):
    return {
        "batch_id": str(batch_id or uuid4()),
        "points": points or [{
            "sequence": 1, "lat": -31.4, "long": -64.2, "speed": 20,
            "heading": 90, "recorded_at": datetime.now(timezone.utc).isoformat(),
        }],
    }


def test_missing_and_invalid_device_auth(client):
    body = payload()
    assert client.post("/devices/ingest", json=body).status_code == 401
    assert client.post("/devices/ingest", json=body, headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_ingest_contract_version_defaults_and_rejects_unknown_version():
    point = payload()["points"][0]
    assert DeviceIngestBatch.model_validate({"batch_id": str(uuid4()), "points": [point]}).v == 1
    assert DeviceIngestBatch.model_validate({"v": 1, "batch_id": str(uuid4()), "points": [point]}).v == 1
    from pydantic import ValidationError
    import pytest
    with pytest.raises(ValidationError):
        DeviceIngestBatch.model_validate({"v": 2, "batch_id": str(uuid4()), "points": [point]})


def test_ingest_point_normalizes_utc_and_heading():
    point = DeviceIngestPoint.model_validate({
        "sequence": 1, "lat": -31.4, "long": -64.2, "speed": 20,
        "heading": 360, "recorded_at": "2026-10-13T12:00:00-03:00",
    })
    assert point.recorded_at.isoformat() == "2026-10-13T15:00:00+00:00"
    assert point.heading == 0


def test_ingest_point_rejects_timestamp_without_timezone():
    from pydantic import ValidationError
    import pytest
    with pytest.raises(ValidationError):
        DeviceIngestPoint.model_validate({
            "sequence": 1, "lat": -31.4, "long": -64.2, "speed": 20,
            "heading": 90, "recorded_at": "2026-10-13T12:00:00",
        })


def test_batch_size_is_one_to_one_hundred(client, test_truck, db_session):
    token = provision_device(db_session, "INGEST-SIZE", test_truck.id)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/devices/ingest", json={"batch_id": str(uuid4()), "points": []}, headers=headers).status_code == 422
    points = [payload()["points"][0] for _ in range(101)]
    assert client.post("/devices/ingest", json=payload(points=points), headers=headers).status_code == 422


def test_one_point_success_and_replay_is_idempotent(client, test_truck, db_session):
    token = provision_device(db_session, "INGEST-OK", test_truck.id)
    body = payload()
    headers = {"Authorization": f"Bearer {token}"}
    first = client.post("/devices/ingest", json=body, headers=headers)
    replay = client.post("/devices/ingest", json=body, headers=headers)
    assert first.status_code == replay.status_code == 200
    assert first.json()["results"][0]["status"] == "accepted"
    assert replay.json()["results"][0]["replayed"] is True
    assert db_session.query(IngestedPoint).count() == 1
    assert db_session.query(TrackingPoint).count() == 1


def test_partial_acceptance_preserves_rejected_raw_payload(client, test_truck, db_session):
    token = provision_device(db_session, "INGEST-PARTIAL", test_truck.id)
    batch = payload(points=[payload()["points"][0], ["malformed"]])
    response = client.post("/devices/ingest", json=batch, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert [result["status"] for result in response.json()["results"]] == ["accepted", "rejected"]
    rejected = db_session.query(RejectedIngestPoint).one()
    assert rejected.raw_payload == '["malformed"]'


def test_assignment_is_resolved_by_recorded_at_and_inactive_truck_rejected(client, test_truck, db_session):
    token = provision_device(db_session, "INGEST-TIME", test_truck.id)
    assignment = db_session.query(DeviceAssignment).one()
    assignment.valid_from = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()
    point_time = datetime.now(timezone.utc) - timedelta(hours=1)
    body = payload(points=[{**payload()["points"][0], "recorded_at": point_time.isoformat()}])
    response = client.post("/devices/ingest", json=body, headers={"Authorization": f"Bearer {token}"})
    assert response.json()["results"][0]["status"] == "accepted"
    test_truck.active = False
    db_session.commit()
    body = payload(points=[{**payload()["points"][0], "sequence": 2, "recorded_at": point_time.isoformat()}])
    response = client.post("/devices/ingest", json=body, headers={"Authorization": f"Bearer {token}"})
    assert response.json()["results"][0]["reason"] == "inactive_truck"


def test_inactive_device_cannot_ingest(client, test_truck, db_session):
    token = provision_device(db_session, "INGEST-INACTIVE", test_truck.id)
    device = db_session.query(Device).filter_by(identifier="INGEST-INACTIVE").one()
    device.active = False
    db_session.commit()
    assert client.post("/devices/ingest", json=payload(), headers={"Authorization": f"Bearer {token}"}).status_code == 401
