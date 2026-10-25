"""Reset de un viaje: la corrida nueva no hereda las paradas de la anterior."""

from datetime import UTC, datetime

from source.main import app
from source.models.destination import Charger, Trip, TripStop
from source.services.auth import get_current_user


def _trip(db_session, org, *, truck=None, status="in_progress"):
    charger = Charger(organization_id=org.id, name="Colchones Sur")
    db_session.add(charger)
    db_session.flush()
    ahora = datetime.now(UTC)
    trip = Trip(
        organization_id=org.id,
        charger_id=charger.id,
        truck_id=truck.id if truck is not None else None,
        departure_at=ahora,
        status=status,
    )
    db_session.add(trip)
    db_session.flush()
    db_session.add_all(
        [
            TripStop(
                trip_id=trip.id,
                seq=1,
                address="Parada 1",
                lat=-31.42,
                lng=-64.18,
                status="delivered",
                arrived_at=ahora,
                departed_at=ahora,
            ),
            TripStop(
                trip_id=trip.id,
                seq=2,
                address="Parada 2",
                lat=-31.41,
                lng=-64.19,
                status="arrived",
                arrived_at=ahora,
            ),
        ]
    )
    db_session.commit()
    return trip


def test_reset_devuelve_el_viaje_a_planificado_con_todas_las_paradas_pendientes(
    admin_client, db_session, test_org, test_truck
):
    trip = _trip(db_session, test_org, truck=test_truck)

    response = admin_client.post(f"/trips/{trip.id}/reset")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "planned"
    assert [stop["status"] for stop in body["stops"]] == ["pending", "pending"]

    db_session.expire_all()
    paradas = (
        db_session.query(TripStop)
        .filter(TripStop.trip_id == trip.id)
        .order_by(TripStop.seq)
        .all()
    )
    assert [parada.status for parada in paradas] == ["pending", "pending"]
    assert all(parada.arrived_at is None for parada in paradas)
    assert all(parada.departed_at is None for parada in paradas)


def test_member_no_puede_resetear_un_viaje(client, test_user, db_session, test_org):
    app.dependency_overrides[get_current_user] = lambda: test_user
    trip = _trip(db_session, test_org)

    assert client.post(f"/trips/{trip.id}/reset").status_code == 403


def test_reset_de_un_viaje_ajeno_responde_404(admin_client, db_session, test_org2):
    ajeno = _trip(db_session, test_org2)

    assert admin_client.post(f"/trips/{ajeno.id}/reset").status_code == 404
