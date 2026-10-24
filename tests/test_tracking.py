from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from source.database.database import get_db
from source.main import app
from source.models.organization import Organization
from source.models.truck import TrackingPoint, Truck
from source.services.auth import get_current_user


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


def test_post_truck_assigns_organization(admin_client, db_session, test_user):
    """POST /trucks asigna automáticamente la organización del usuario."""
    response = admin_client.post(
        "/trucks",
        json={"id": 2, "plate": "NEW123"},
    )
    assert response.status_code == 200

    # Verificar que el camión tiene la organización correcta
    truck = db_session.query(Truck).filter(Truck.plate == "NEW123").first()
    assert truck is not None
    assert truck.organization_id == test_user.organization_id
    # El alta no escribe telemetría: eso es exclusivo de POST /devices/ingest.
    assert db_session.query(TrackingPoint).filter(TrackingPoint.truck_id == truck.id).count() == 0


def test_post_truck_defaults_to_active(admin_client, db_session):
    response = admin_client.post(
        "/trucks",
        json={"id": 2, "plate": "ACTIVE1"},
    )

    assert response.status_code == 200
    truck = db_session.query(Truck).filter(Truck.id == 2).one()
    assert truck.active is True


def test_users_cannot_push_locations(tracking_client, test_truck):
    """La telemetría humana ya no existe: solo POST /devices/ingest escribe puntos."""
    response = tracking_client.put(
        f"/trucks/{test_truck.id}/location",
        json={"lat": -31.42, "long": -64.18, "speed": 0, "heading": 0},
    )

    assert response.status_code == 405


def test_get_location_other_org_truck_returns_404(tracking_client, other_truck):
    """GET /{truck_id}/location con camión de otra organización → 404."""
    response = tracking_client.get(f"/trucks/{other_truck.id}/location")
    assert response.status_code == 404


def test_get_iter_other_org_truck_returns_404(tracking_client, other_truck):
    """GET /{truck_id}/iter con camión de otra organización → 404."""
    response = tracking_client.get(f"/trucks/{other_truck.id}/iter")
    assert response.status_code == 404


def test_delete_iter_other_org_truck_returns_404(admin_client, other_truck):
    """DELETE /{truck_id}/iter con camión de otra organización → 404."""
    response = admin_client.delete(f"/trucks/{other_truck.id}/iter")
    assert response.status_code == 404


def test_get_truck_ids_only_returns_own_org(tracking_client, test_truck, other_truck):
    """GET /trucks/ids solo devuelve camiones de la organización del usuario."""
    response = tracking_client.get("/trucks/ids")
    assert response.status_code == 200
    trucks = response.json()
    plates = [t["plate"] for t in trucks]
    assert "TEST123" in plates
    assert "OTHER99" not in plates


def test_location_responses_include_telemetry(tracking_client, db_session, test_truck):
    db_session.add_all([
        TrackingPoint(truck_id=test_truck.id, lat=-31.42, long=-64.18, speed=10, heading=90),
        TrackingPoint(truck_id=test_truck.id, lat=-31.43, long=-64.19, speed=20, heading=270),
    ])
    db_session.commit()

    latest = tracking_client.get(f"/trucks/{test_truck.id}/location")
    history = tracking_client.get(f"/trucks/{test_truck.id}/iter")

    assert latest.status_code == 200
    assert latest.json()["speed"] == 20
    assert latest.json()["heading"] == 270
    assert history.status_code == 200
    assert {point["speed"] for point in history.json()} == {10, 20}
    assert {point["heading"] for point in history.json()} == {90, 270}


# Orden de lectura: hora de medición (recorded_at), no hora de llegada al servidor (timestamp)
MEASURED_BASE = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)


def _store_point(db_session, truck_id, *, speed, measured_at, server_timestamp):
    """Punto con su medición (recorded_at, UTC) y su llegada al servidor (timestamp, naive)."""
    db_session.add(TrackingPoint(
        truck_id=truck_id,
        lat=-31.42,
        long=-64.18,
        speed=speed,
        heading=0,
        recorded_at=measured_at,
        timestamp=server_timestamp,
    ))
    db_session.commit()


def test_get_location_orders_by_measurement_time_not_arrival(tracking_client, db_session, test_truck):
    """Un lote atrasado llega después pero se midió antes: no es la ubicación más reciente."""
    _store_point(db_session, test_truck.id, speed=10,
                 measured_at=MEASURED_BASE + timedelta(seconds=10),
                 server_timestamp=datetime(2026, 10, 13, 12, 0, 11))
    _store_point(db_session, test_truck.id, speed=20,
                 measured_at=MEASURED_BASE + timedelta(seconds=1),
                 server_timestamp=datetime(2026, 10, 13, 12, 0, 12))

    response = tracking_client.get(f"/trucks/{test_truck.id}/location")

    assert response.status_code == 200
    assert response.json()["speed"] == 10


def test_get_iter_orders_newest_first_by_measurement_time(tracking_client, db_session, test_truck):
    """El historial va del más nuevo al más antiguo según la medición, no según la llegada."""
    _store_point(db_session, test_truck.id, speed=10,
                 measured_at=MEASURED_BASE + timedelta(seconds=10),
                 server_timestamp=datetime(2026, 10, 13, 12, 0, 11))
    _store_point(db_session, test_truck.id, speed=20,
                 measured_at=MEASURED_BASE + timedelta(seconds=1),
                 server_timestamp=datetime(2026, 10, 13, 12, 0, 12))
    _store_point(db_session, test_truck.id, speed=30,
                 measured_at=MEASURED_BASE + timedelta(seconds=2),
                 server_timestamp=datetime(2026, 10, 13, 12, 0, 13))

    response = tracking_client.get(f"/trucks/{test_truck.id}/iter")

    assert response.status_code == 200
    assert [point["speed"] for point in response.json()] == [10, 30, 20]
    assert all("recorded_at" in point for point in response.json())


def test_get_iter_limit_is_validated_and_applied(tracking_client, db_session, test_truck):
    for index in range(6):
        db_session.add(TrackingPoint(
            truck_id=test_truck.id, lat=-31.42, long=-64.18, speed=index, heading=0,
            recorded_at=datetime.now(UTC) - timedelta(minutes=index),
        ))
    db_session.commit()
    assert len(tracking_client.get(f"/trucks/{test_truck.id}/iter").json()) == 6
    assert len(tracking_client.get(f"/trucks/{test_truck.id}/iter?limit=5").json()) == 5
    assert tracking_client.get(f"/trucks/{test_truck.id}/iter?limit=0").status_code == 422
    assert tracking_client.get(f"/trucks/{test_truck.id}/iter?limit=1001").status_code == 422


def test_reads_break_measurement_ties_by_newest_insert(tracking_client, db_session, test_truck):
    """Dos puntos con la misma medición: gana el insertado último, en ambas lecturas."""
    _store_point(db_session, test_truck.id, speed=10, measured_at=MEASURED_BASE,
                 server_timestamp=datetime(2026, 10, 13, 12, 0, 11))
    _store_point(db_session, test_truck.id, speed=20, measured_at=MEASURED_BASE,
                 server_timestamp=datetime(2026, 10, 13, 12, 0, 12))

    latest = tracking_client.get(f"/trucks/{test_truck.id}/location")
    history = tracking_client.get(f"/trucks/{test_truck.id}/iter")

    assert latest.json()["speed"] == 20
    assert [point["speed"] for point in history.json()] == [20, 10]


def test_tracking_point_distinguishes_recorded_and_received_time(db_session, test_truck):
    """recorded_at es la medición; received_at es la recepción en el servidor."""
    measured_at = datetime(2026, 10, 1, 8, 30, 0)
    point = TrackingPoint(
        truck_id=test_truck.id,
        lat=-31.42,
        long=-64.18,
        speed=10,
        heading=90,
        recorded_at=measured_at,
    )
    db_session.add(point)
    db_session.commit()
    db_session.refresh(point)

    assert point.recorded_at == measured_at
    assert point.received_at is not None
    assert point.received_at > point.recorded_at


def test_tracking_point_received_at_defaults_to_now(db_session, test_truck):
    before = datetime.now(UTC).replace(tzinfo=None)
    point = TrackingPoint(truck_id=test_truck.id, lat=-31.42, long=-64.18, speed=0, heading=0)
    db_session.add(point)
    db_session.commit()
    db_session.refresh(point)

    assert point.recorded_at is not None
    assert point.received_at is not None
    assert point.received_at >= before
