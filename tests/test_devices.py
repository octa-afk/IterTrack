import re
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from source.models.device import Device, DeviceAssignment
from source.services.devices import generate_device_token, hash_device_token, provision_device


def open_assignments_for_truck(db_session, truck_id):
    return (
        db_session.query(DeviceAssignment)
        .filter(DeviceAssignment.truck_id == truck_id, DeviceAssignment.valid_to.is_(None))
        .all()
    )


def test_hash_device_token_is_deterministic_sha256_hex():
    token = "some-token"
    digest = hash_device_token(token)

    assert digest == hash_device_token(token)
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert digest != token


def test_generate_device_token_is_unique_and_long():
    first = generate_device_token()
    second = generate_device_token()

    assert first != second
    assert len(first) >= 40


def test_provision_device_returns_token_and_stores_only_hash(db_session, test_truck):
    token = provision_device(db_session, "AA:BB:CC:DD:EE:01", test_truck.id)

    device = db_session.query(Device).filter_by(identifier="AA:BB:CC:DD:EE:01").one()
    assert device.token_hash == hash_device_token(token)
    assert device.active is True
    assert token not in (device.identifier, device.token_hash)


def test_provision_device_creates_exactly_one_open_assignment(db_session, test_truck):
    provision_device(db_session, "AA:BB:CC:DD:EE:02", test_truck.id)

    assignments = open_assignments_for_truck(db_session, test_truck.id)
    assert len(assignments) == 1
    assert assignments[0].valid_to is None


def test_provision_device_rejects_duplicate_identifier(db_session, test_truck):
    provision_device(db_session, "AA:BB:CC:DD:EE:03", test_truck.id)

    with pytest.raises(ValueError):
        provision_device(db_session, "AA:BB:CC:DD:EE:03", test_truck.id)


def test_provision_device_rejects_unknown_truck(db_session):
    with pytest.raises(ValueError):
        provision_device(db_session, "AA:BB:CC:DD:EE:04", 999)


def test_provision_device_rejects_empty_identifier(db_session, test_truck):
    with pytest.raises(ValueError):
        provision_device(db_session, "   ", test_truck.id)


def test_truck_with_open_assignment_cannot_get_second_device(db_session, test_truck):
    provision_device(db_session, "AA:BB:CC:DD:EE:05", test_truck.id)

    with pytest.raises(ValueError):
        provision_device(db_session, "AA:BB:CC:DD:EE:06", test_truck.id)


def test_device_cannot_have_two_open_assignments_at_db_level(db_session, test_truck):
    provision_device(db_session, "AA:BB:CC:DD:EE:07", test_truck.id)
    device = db_session.query(Device).filter_by(identifier="AA:BB:CC:DD:EE:07").one()

    db_session.add(DeviceAssignment(device_id=device.id, truck_id=test_truck.id + 1000))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_truck_cannot_have_two_open_assignments_at_db_level(db_session, test_truck):
    provision_device(db_session, "AA:BB:CC:DD:EE:08", test_truck.id)
    other = Device(identifier="AA:BB:CC:DD:EE:09", token_hash=hash_device_token("x"))
    db_session.add(other)
    db_session.commit()

    db_session.add(DeviceAssignment(device_id=other.id, truck_id=test_truck.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_closed_assignment_does_not_block_new_open_one(db_session, test_truck):
    provision_device(db_session, "AA:BB:CC:DD:EE:10", test_truck.id)
    closed = open_assignments_for_truck(db_session, test_truck.id)[0]
    closed.valid_to = datetime.now(timezone.utc)
    db_session.commit()

    other = Device(identifier="AA:BB:CC:DD:EE:11", token_hash=hash_device_token("y"))
    db_session.add(other)
    db_session.commit()
    db_session.add(DeviceAssignment(device_id=other.id, truck_id=test_truck.id))
    db_session.commit()

    assert len(open_assignments_for_truck(db_session, test_truck.id)) == 1
