"""Progreso automático del viaje: el camión mueve el estado, no el operador."""

from datetime import UTC, datetime
from uuid import uuid4

from source.models.destination import Charger, Depot, Trip, TripStop
from source.services.devices import provision_device
from source.services.trip_progress import STOP_RADIUS_M, advance_trip_progress

# Un punto del centro de Córdoba, y otro a ~1,1 km para quedar fuera de radio.
STOP = (-31.4200, -64.1800)
FAR = (-31.4300, -64.1800)


def _trip(db_session, test_org, test_truck, *, depot=None, status="planned", stops=()):
    charger = Charger(organization_id=test_org.id, name=f"Dador {uuid4().hex[:6]}")
    db_session.add(charger)
    db_session.flush()
    trip = Trip(
        organization_id=test_org.id,
        charger_id=charger.id,
        truck_id=test_truck.id,
        departure_at=datetime.now(UTC),
        status=status,
        depot_id=depot.id if depot is not None else None,
    )
    db_session.add(trip)
    db_session.flush()
    for seq, (lat, lng) in enumerate(stops, start=1):
        db_session.add(
            TripStop(
                trip_id=trip.id,
                seq=seq,
                address=f"Parada {seq}",
                lat=lat,
                lng=lng,
                geo_source="provided",
            )
        )
    db_session.commit()
    return trip


def _depot(db_session, test_org, lat, lng, radius_m=150):
    depot = Depot(
        organization_id=test_org.id, name=f"Depósito {uuid4().hex[:6]}", lat=lat, lng=lng,
        radius_m=radius_m,
    )
    db_session.add(depot)
    db_session.commit()
    return depot


def _advance(db_session, test_truck, point, measured_at=None):
    return advance_trip_progress(
        db_session,
        truck_id=test_truck.id,
        lat=point[0],
        lng=point[1],
        measured_at=measured_at or datetime.now(UTC),
    )


def test_arriving_at_the_depot_starts_a_planned_trip(
    db_session, test_org, test_truck
):
    depot = _depot(db_session, test_org, *STOP)
    trip = _trip(db_session, test_org, test_truck, depot=depot)

    _advance(db_session, test_truck, STOP)

    assert trip.status == "in_progress"


def test_a_point_outside_the_depot_radius_does_not_start_the_trip(
    db_session, test_org, test_truck
):
    depot = _depot(db_session, test_org, *STOP)
    trip = _trip(db_session, test_org, test_truck, depot=depot)

    _advance(db_session, test_truck, FAR)

    assert trip.status == "planned"


def test_a_stop_is_arrived_on_entry_and_delivered_on_exit(
    db_session, test_org, test_truck
):
    trip = _trip(db_session, test_org, test_truck, stops=[STOP])
    stop = trip.stops[0]
    measured_at = datetime.now(UTC)

    _advance(db_session, test_truck, STOP, measured_at)
    assert stop.status == "arrived"
    assert stop.arrived_at == measured_at
    assert trip.status == "in_progress"

    salida = datetime.now(UTC)
    _advance(db_session, test_truck, FAR, salida)
    assert stop.status == "delivered"
    assert stop.departed_at == salida


def test_the_trip_is_done_when_every_stop_is_delivered(
    db_session, test_org, test_truck
):
    trip = _trip(db_session, test_org, test_truck, stops=[STOP])

    _advance(db_session, test_truck, STOP)
    assert trip.status == "in_progress"

    _advance(db_session, test_truck, FAR)

    assert trip.status == "done"


def test_a_later_stop_is_not_delivered_before_the_next_one_in_order(
    db_session, test_org, test_truck
):
    """El viaje es secuencial: pasar cerca de la 2 no reemplaza llegar a la 1."""
    parada1 = (-31.4200, -64.1800)
    parada2 = (-31.4100, -64.1800)
    parada3 = (-31.4000, -64.1800)
    trip = _trip(db_session, test_org, test_truck, stops=[parada1, parada2, parada3])

    _advance(db_session, test_truck, parada2)

    assert [stop.status for stop in trip.stops] == ["pending", "pending", "pending"]

    _advance(db_session, test_truck, parada1)
    assert trip.stops[0].status == "arrived"

    _advance(db_session, test_truck, FAR)
    assert trip.stops[0].status == "delivered"

    _advance(db_session, test_truck, parada2)
    assert trip.stops[1].status == "arrived"
    assert trip.stops[2].status == "pending"


def test_a_stop_without_coordinates_keeps_the_trip_open(
    db_session, test_org, test_truck
):
    """Una parada sin ubicar no se puede entregar: darla por hecha sería inventar."""
    trip = _trip(db_session, test_org, test_truck, stops=[STOP])
    db_session.add(
        TripStop(trip_id=trip.id, seq=2, address="Ruta 9 km 720", needs_review=True)
    )
    db_session.commit()

    _advance(db_session, test_truck, STOP)
    _advance(db_session, test_truck, FAR)

    assert trip.stops[0].status == "delivered"
    assert trip.stops[1].status == "pending"
    assert trip.status == "in_progress"


def test_a_truck_without_an_open_trip_is_ignored(db_session, test_org, test_truck):
    _trip(db_session, test_org, test_truck, status="done", stops=[STOP])

    assert _advance(db_session, test_truck, STOP) is None


def test_ingest_advances_the_trip_of_the_device(
    client, db_session, test_org, test_truck
):
    """El cableado: un punto aceptado por la ingesta mueve el viaje."""
    trip = _trip(db_session, test_org, test_truck, stops=[STOP])
    token = provision_device(db_session, "PROGRESS-01", test_truck.id)

    response = client.post(
        "/devices/ingest",
        json={
            "batch_id": str(uuid4()),
            "points": [
                {
                    "sequence": 1,
                    "lat": STOP[0],
                    "long": STOP[1],
                    "speed": 20,
                    "heading": 90,
                    "recorded_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.json()["results"][0]["status"] == "accepted"
    db_session.refresh(trip.stops[0])
    assert trip.stops[0].status == "arrived"
    assert trip.stops[0].arrived_at is not None


def test_the_stop_radius_is_generous_enough_for_a_sidewalk():
    """Un destino es una dirección: 120 m cubre vereda de enfrente y error de GPS."""
    assert STOP_RADIUS_M == 120
