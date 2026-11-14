"""GET /trucks/live: la flota en un pedido, con el último punto medido de cada camión."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from source.database.database import get_db
from source.main import app
from source.models.organization import Organization
from source.models.truck import TrackingPoint, Truck
from source.services.auth import get_current_user


@pytest.fixture()
def live_client(db_session, test_user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _point(db_session, truck_id, *, lat=-31.4, lng=-64.2, speed=40.0, heading=90.0,
           minutes_ago=0.0, received_minutes_ago=None):
    recorded = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    received = (
        datetime.now(UTC) - timedelta(minutes=received_minutes_ago)
        if received_minutes_ago is not None
        else recorded
    )
    db_session.add(
        TrackingPoint(
            truck_id=truck_id, lat=lat, long=lng, speed=speed, heading=heading,
            recorded_at=recorded, received_at=received,
        )
    )
    db_session.commit()


def _by_id(response):
    assert response.status_code == 200
    return {truck["id"]: truck for truck in response.json()}


def test_devuelve_el_ultimo_punto_con_lo_que_informo_el_equipo(live_client, db_session, test_truck):
    _point(db_session, test_truck.id, lat=-31.40, speed=20, minutes_ago=2)
    _point(db_session, test_truck.id, lat=-31.41, lng=-64.21, speed=47.5, heading=270, minutes_ago=1)

    truck = _by_id(live_client.get("/trucks/live"))[test_truck.id]

    assert truck["plate"] == "TEST123"
    assert truck["active"] is True
    assert (truck["lat"], truck["lng"]) == (-31.41, -64.21)
    assert truck["speed"] == 47.5
    assert truck["heading"] == 270
    assert truck["status"] == "move"
    # Con zona horaria: sin ella el navegador la lee como hora local.
    assert datetime.fromisoformat(truck["recorded_at"]).tzinfo is not None


def test_gana_el_ultimo_medido_aunque_haya_llegado_antes(live_client, db_session, test_truck):
    """Un punto guardado sin señal llega tarde: no puede pisar la posición actual."""
    _point(db_session, test_truck.id, lat=-31.50, minutes_ago=1, received_minutes_ago=1)
    _point(db_session, test_truck.id, lat=-31.90, minutes_ago=30, received_minutes_ago=0)

    assert _by_id(live_client.get("/trucks/live"))[test_truck.id]["lat"] == -31.50


def test_un_camion_sin_puntos_aparece_sin_posicion(live_client, test_truck):
    truck = _by_id(live_client.get("/trucks/live"))[test_truck.id]

    assert truck["lat"] is None and truck["lng"] is None
    assert truck["recorded_at"] is None
    assert truck["status"] == "stop"


@pytest.mark.parametrize(
    ("speed", "minutes_ago", "status"),
    [
        (40, 1, "move"),
        (1, 1, "idle"),
        (120, 1, "alert"),
        (40, 15, "stop"),  # sin reportar hace más de 10 minutos
    ],
)
def test_el_estado_lo_calcula_el_servidor(live_client, db_session, test_truck, speed, minutes_ago, status):
    _point(db_session, test_truck.id, speed=speed, minutes_ago=minutes_ago)

    assert _by_id(live_client.get("/trucks/live"))[test_truck.id]["status"] == status


def test_solo_devuelve_camiones_de_la_organizacion(live_client, db_session, test_truck):
    otra = Organization(name="Otra", invitation_code="OTRA")
    db_session.add(otra)
    db_session.flush()
    db_session.add(Truck(id=99, plate="AJENO99", organization_id=otra.id))
    db_session.commit()
    _point(db_session, 99)

    assert set(_by_id(live_client.get("/trucks/live"))) == {test_truck.id}


def test_varios_camiones_en_un_solo_pedido(live_client, db_session, test_org, test_truck):
    db_session.add(Truck(id=2, plate="SEG222", organization_id=test_org.id))
    db_session.commit()
    _point(db_session, test_truck.id, lat=-31.1)
    _point(db_session, 2, lat=-31.2)

    trucks = _by_id(live_client.get("/trucks/live"))

    assert trucks[test_truck.id]["lat"] == -31.1
    assert trucks[2]["lat"] == -31.2


def test_requiere_autenticacion(client):
    app.dependency_overrides.pop(get_current_user)
    assert client.get("/trucks/live").status_code == 401
