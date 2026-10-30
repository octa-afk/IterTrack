"""Ruta por calles del viaje abierto.

OSRM se inyecta como dependencia, igual que el geocoder: estos tests le pasan un
doble y nunca salen a la red. Lo que se verifica es el armado de los puntos
—última posición del camión, paradas pendientes en orden, coordenadas sin
resolver salteadas— y el aislamiento por organización.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from source.main import app
from source.models.destination import Charger, Depot, Trip, TripStop
from source.models.truck import TrackingPoint
from source.services.routing import OsrmRouter, RouteResult, get_router


class FakeRouter:
    name = "fake"

    def __init__(self, result=None):
        self.result = result
        self.calls: list[list[tuple[float, float]]] = []

    def route(self, points):
        self.calls.append(points)
        return self.result


@pytest.fixture()
def usar_router():
    """Instala el doble como dependencia y lo devuelve."""

    def _install(result=None):
        fake = FakeRouter(result)
        app.dependency_overrides[get_router] = lambda: fake
        return fake

    yield _install
    app.dependency_overrides.pop(get_router, None)


def _trip(db_session, org, *, truck=None, depot=None, stops=()):
    charger = (
        db_session.query(Charger)
        .filter(Charger.organization_id == org.id)
        .first()
    )
    if charger is None:
        charger = Charger(organization_id=org.id, name="Colchones Sur")
        db_session.add(charger)
        db_session.flush()
    trip = Trip(
        organization_id=org.id,
        charger_id=charger.id,
        truck_id=truck.id if truck is not None else None,
        depot_id=depot.id if depot is not None else None,
        departure_at=datetime.now(UTC),
    )
    db_session.add(trip)
    db_session.flush()
    for seq, (lat, lng, status) in enumerate(stops, start=1):
        db_session.add(
            TripStop(
                trip_id=trip.id,
                seq=seq,
                address=f"Destino {seq}",
                lat=lat,
                lng=lng,
                status=status,
            )
        )
    db_session.commit()
    db_session.refresh(trip)
    return trip


def _point(db_session, truck, lat, lng, minutes_ago=0):
    now = datetime.now(UTC)
    db_session.add(
        TrackingPoint(
            truck_id=truck.id,
            lat=lat,
            lng=lng,
            speed=50,
            heading=90,
            recorded_at=now - timedelta(minutes=minutes_ago),
            received_at=now - timedelta(minutes=minutes_ago),
        )
    )
    db_session.commit()


RUTA = RouteResult(
    points=[(-31.4, -64.2), (-31.41, -64.19), (-31.42, -64.18)],
    distance_m=12345.6,
    duration_s=900.0,
    provider="fake",
)


def test_ruta_va_solo_a_la_proxima_parada_pendiente(
    admin_client, db_session, test_org, test_truck, usar_router
):
    # El punto más nuevo manda: el orden es por recorded_at, no por id.
    _point(db_session, test_truck, -31.30, -64.30, minutes_ago=10)
    _point(db_session, test_truck, -31.40, -64.20, minutes_ago=1)
    trip = _trip(
        db_session,
        test_org,
        truck=test_truck,
        stops=[
            (-31.41, -64.19, "pending"),
            (-31.45, -64.15, "delivered"),
            (None, None, "pending"),
            (-31.42, -64.18, "arrived"),
        ],
    )
    fake = usar_router(RUTA)

    response = admin_client.get(f"/trips/{trip.id}/route")

    assert response.status_code == 200, response.text
    # Sólo la parada 1: la 2 está entregada y la 4 todavía no toca.
    assert fake.calls == [[(-31.40, -64.20), (-31.41, -64.19)]]
    body = response.json()
    assert body["trip_id"] == trip.id
    assert body["stop_id"] == trip.stops[0].id
    assert body["stop_seq"] == 1
    assert body["distance_m"] == 12345.6
    assert body["duration_s"] == 900.0
    assert body["provider"] == "fake"
    assert body["geometry"][0] == [-31.4, -64.2]


def test_las_paradas_se_recorren_por_seq_no_por_orden_de_insercion(
    admin_client, db_session, test_org, test_truck, usar_router
):
    _point(db_session, test_truck, -31.40, -64.20)
    trip = _trip(db_session, test_org, truck=test_truck, stops=[])
    # La base las devuelve por seq, no por id: la parada 2 se insertó primero.
    db_session.add_all(
        [
            TripStop(
                trip_id=trip.id,
                seq=2,
                address="Parada 2",
                lat=-31.42,
                lng=-64.18,
                status="pending",
            ),
            TripStop(
                trip_id=trip.id,
                seq=1,
                address="Parada 1",
                lat=-31.41,
                lng=-64.19,
                status="pending",
            ),
        ]
    )
    db_session.commit()
    fake = usar_router(RUTA)

    response = admin_client.get(f"/trips/{trip.id}/route")

    assert response.status_code == 200, response.text
    # La 1 primero aunque se haya insertado después: manda `seq`, no el id.
    assert fake.calls == [[(-31.40, -64.20), (-31.41, -64.19)]]
    assert response.json()["stop_seq"] == 1


def test_una_parada_ya_alcanzada_no_es_el_destino_de_la_ruta(
    admin_client, db_session, test_org, test_truck, usar_router
):
    """Si el camión ya está en la parada 1, la ruta apunta a la 2."""
    _point(db_session, test_truck, -31.40, -64.20)
    trip = _trip(
        db_session,
        test_org,
        truck=test_truck,
        stops=[
            (-31.41, -64.19, "arrived"),
            (-31.42, -64.18, "pending"),
        ],
    )
    fake = usar_router(RUTA)

    response = admin_client.get(f"/trips/{trip.id}/route")

    assert response.status_code == 200, response.text
    assert fake.calls == [[(-31.40, -64.20), (-31.42, -64.18)]]
    assert response.json()["stop_seq"] == 2


def test_sin_posicion_del_camion_el_origen_es_el_deposito(
    admin_client, db_session, test_org, test_truck, usar_router
):
    depot = Depot(
        organization_id=test_org.id, name="Depósito Centro", lat=-31.42, lng=-64.19
    )
    db_session.add(depot)
    db_session.commit()
    db_session.refresh(depot)
    trip = _trip(
        db_session,
        test_org,
        truck=test_truck,
        depot=depot,
        stops=[(-31.41, -64.19, "pending")],
    )
    fake = usar_router(RUTA)

    response = admin_client.get(f"/trips/{trip.id}/route")

    assert response.status_code == 200, response.text
    assert fake.calls == [[(-31.42, -64.19), (-31.41, -64.19)]]


def test_sin_origen_ni_paradas_ubicadas_responde_409(
    admin_client, db_session, test_org, test_truck, usar_router
):
    # Sin camión asignado ni depósito: no hay desde dónde arrancar.
    sin_origen = _trip(db_session, test_org, stops=[(-31.41, -64.19, "pending")])
    usar_router(RUTA)
    assert admin_client.get(f"/trips/{sin_origen.id}/route").status_code == 409

    # Hay origen, pero la única parada no tiene coordenada: no hay a dónde ir.
    sin_paradas = _trip(
        db_session,
        test_org,
        truck=test_truck,
        stops=[(None, None, "pending")],
    )
    assert admin_client.get(f"/trips/{sin_paradas.id}/route").status_code == 409


def test_sin_proveedor_de_ruteo_responde_503(admin_client, db_session, test_org, test_truck):
    _point(db_session, test_truck, -31.40, -64.20)
    trip = _trip(
        db_session,
        test_org,
        truck=test_truck,
        stops=[(-31.41, -64.19, "pending")],
    )

    response = admin_client.get(f"/trips/{trip.id}/route")

    assert response.status_code == 503
    assert "ruteo" in response.json()["detail"].lower()


def test_viaje_de_otra_organizacion_responde_404(
    admin_client, db_session, test_org2, usar_router
):
    ajeno = _trip(db_session, test_org2, stops=[(-31.41, -64.19, "pending")])
    usar_router(RUTA)

    assert admin_client.get(f"/trips/{ajeno.id}/route").status_code == 404


def test_osrm_router_parsea_geometria_y_respeta_lon_lat(monkeypatch):
    class Respuesta:
        status_code = 200

        @staticmethod
        def json():
            return {
                "code": "Ok",
                "routes": [
                    {
                        "distance": 1500.0,
                        "duration": 120.0,
                        "geometry": {
                            "coordinates": [[-64.19, -31.41], [-64.18, -31.42]]
                        },
                    }
                ],
            }

    pedidas: list[str] = []

    def get(url, **kwargs):
        pedidas.append(url)
        return Respuesta()

    monkeypatch.setattr("source.services.routing.httpx.get", get)

    resultado = OsrmRouter().route([(-31.40, -64.20), (-31.42, -64.18)])

    assert resultado is not None
    assert "-64.2,-31.4;-64.18,-31.42" in pedidas[0]
    assert resultado.points == [(-31.41, -64.19), (-31.42, -64.18)]
    assert resultado.distance_m == 1500.0
    assert resultado.duration_s == 120.0


def test_osrm_router_devuelve_none_si_el_proveedor_falla(monkeypatch):
    def caido(url, **kwargs):
        raise httpx.ConnectError("sin red")

    monkeypatch.setattr("source.services.routing.httpx.get", caido)
    assert OsrmRouter().route([(-31.40, -64.20), (-31.42, -64.18)]) is None


def test_osrm_router_no_llama_con_un_solo_punto(monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "source.services.routing.httpx.get", lambda *a, **k: llamadas.append(a)
    )
    assert OsrmRouter().route([(-31.40, -64.20)]) is None
    assert llamadas == []


def test_osrm_router_devuelve_none_si_responde_error(monkeypatch):
    class Respuesta:
        status_code = 500

        @staticmethod
        def json():
            return {}

    monkeypatch.setattr(
        "source.services.routing.httpx.get", lambda *a, **k: Respuesta()
    )
    assert OsrmRouter().route([(-31.40, -64.20), (-31.42, -64.18)]) is None
