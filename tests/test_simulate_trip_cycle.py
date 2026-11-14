"""El simulador hace el mismo viaje que dibuja el mapa, contra la API real.

API, ingesta y progreso automático son los de verdad (SQLite en memoria); el
único doble es el proveedor de ruteo, que devuelve una recta densa del camión a
la parada. Lo que se verifica es que el camión recorra *esa* geometría de punta
a punta del viaje: sin irse al circuito fijo, sin saltos y sin terminar un
tramo que el mapa ya no muestra.
"""

from datetime import UTC, datetime
from itertools import pairwise
from urllib.parse import urlsplit

import pytest

import scripts.simulate_trucks as sim
from source.main import app
from source.models.destination import Charger, Depot, Trip, TripStop
from source.services.devices import provision_device
from source.services.routing import RouteResult, get_router

DEPOSITO = (-31.4060, -64.1950)
PARADAS = [(-31.4100, -64.1900), (-31.4140, -64.1850), (-31.4180, -64.1900)]
# Lejos de todo: un punto cerca de acá significa que el camión se fue al circuito.
CIRCUITO = [[-31.30, -64.40], [-31.31, -64.41], [-31.30, -64.40]]
PASO_M = 25.0
RADIO_PARADA_M = 120


def _distancia(a, b) -> float:
    return sim.calcular_distancia_metros(a[0], a[1], b[0], b[1])


def _recta(desde, hasta):
    pasos = int(_distancia(desde, hasta) // PASO_M) + 1
    return [
        (
            desde[0] + (hasta[0] - desde[0]) * k / pasos,
            desde[1] + (hasta[1] - desde[1]) * k / pasos,
        )
        for k in range(pasos + 1)
    ]


class RouterRecto:
    """Como OSRM, pero la calle es una recta densa: alcanza para seguirla."""

    name = "fake"

    def __init__(self, fallas=()):
        self.pedidos = 0
        self.fallas = set(fallas)

    def route(self, points):
        self.pedidos += 1
        if self.pedidos in self.fallas:
            return None  # proveedor caído: la API responde 502
        desde, hasta = points
        return RouteResult(
            points=_recta(desde, hasta),
            distance_m=_distancia(desde, hasta),
            duration_s=1.0,
            provider=self.name,
        )


class Parar:
    """StopSignal que corta después de una cantidad de esperas, sin dormir."""

    def __init__(self, esperas: int):
        self.restantes = esperas

    def is_set(self) -> bool:
        return self.restantes <= 0

    def wait(self, _timeout=None) -> bool:
        self.restantes -= 1
        return self.is_set()

    def set(self) -> None:
        self.restantes = 0


@pytest.fixture()
def demo(db_session, test_org, test_truck, admin_client, monkeypatch):
    """Viaje de tres paradas para el camión 1 y el simulador hablando con la API de prueba."""
    depot = Depot(
        organization_id=test_org.id,
        name="Depósito",
        lat=DEPOSITO[0],
        lng=DEPOSITO[1],
        radius_m=150,
    )
    charger = Charger(organization_id=test_org.id, name="Dador")
    db_session.add_all([depot, charger])
    db_session.flush()
    trip = Trip(
        organization_id=test_org.id,
        charger_id=charger.id,
        truck_id=test_truck.id,
        depot_id=depot.id,
        departure_at=datetime.now(UTC),
        status="planned",
    )
    db_session.add(trip)
    db_session.flush()
    for seq, (lat, lng) in enumerate(PARADAS, start=1):
        db_session.add(
            TripStop(trip_id=trip.id, seq=seq, address=f"Parada {seq}", lat=lat, lng=lng)
        )
    db_session.commit()
    token = provision_device(db_session, "SIM-001", test_truck.id)

    def get(url, params=None, headers=None, timeout=None):
        return admin_client.get(urlsplit(url).path, params=params, headers=headers)

    def post(url, json=None, data=None, headers=None, timeout=None):
        return admin_client.post(urlsplit(url).path, json=json, data=data, headers=headers)

    monkeypatch.setattr("scripts.simulate_trucks.requests.get", get)
    monkeypatch.setattr("scripts.simulate_trucks.requests.post", post)
    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda *_: CIRCUITO)
    yield trip, token
    app.dependency_overrides.pop(get_router, None)


def _correr(db_session, trip, token, esperas, router, al_emitir=None):
    """Corre el simulador y anota, por punto, la posición y el estado del viaje."""
    app.dependency_overrides[get_router] = lambda: router
    enviar = sim.constructor_de_sender(token)
    registro: list[tuple[float, float, str, str]] = []

    def sender(lat, lon, velocidad, rumbo, medido_en):
        ok = enviar(lat, lon, velocidad, rumbo, medido_en)
        db_session.expire_all()
        viaje = db_session.get(Trip, trip.id)
        registro.append(
            (lat, lon, viaje.status, "".join(stop.status[0] for stop in viaje.stops))
        )
        if al_emitir is not None:
            al_emitir(len(registro))
        return ok

    sim.simular_ruta(
        trip.truck_id,
        "TEST123",
        0,
        Parar(esperas),
        admin_headers={"Authorization": "Bearer admin"},
        sender=sender,
    )
    return registro


def _sin_circuito_ni_saltos(registro):
    posiciones = [(lat, lng) for lat, lng, *_ in registro]
    assert all(_distancia(p, CIRCUITO[0]) > 5_000 for p in posiciones)
    assert max(_distancia(a, b) for a, b in pairwise(posiciones)) <= PASO_M + 1


def test_hace_el_viaje_entero_y_lo_reabre_sin_irse_al_circuito(demo, db_session):
    trip, token = demo

    registro = _correr(db_session, trip, token, esperas=220, router=RouterRecto())

    estados = [(estado, paradas) for *_, estado, paradas in registro]
    # Las tres paradas en orden y el viaje cerrado al entregar la última.
    vistos = list(dict.fromkeys(estados))
    assert vistos[:7] == [
        ("in_progress", "ppp"),
        ("in_progress", "app"),
        ("in_progress", "dpp"),
        ("in_progress", "dap"),
        ("in_progress", "ddp"),
        ("in_progress", "dda"),
        ("done", "ddd"),
    ]
    # Se reabrió y volvió a llegar a la parada 1.
    cierre = estados.index(("done", "ddd"))
    assert ("in_progress", "app") in estados[cierre:]
    _sin_circuito_ni_saltos(registro)


def test_si_reemplazan_el_viaje_a_mitad_de_tramo_va_directo_a_la_parada_nueva(
    demo, db_session
):
    trip, token = demo
    nueva = (-31.4000, -64.2050)  # del otro lado del depósito que la parada 1
    cambio = 10

    def reemplazar(emitidos: int) -> None:
        if emitidos != cambio:
            return
        trip.status = "cancelled"
        otro = Trip(
            organization_id=trip.organization_id,
            charger_id=trip.charger_id,
            truck_id=trip.truck_id,
            departure_at=datetime.now(UTC),
            status="planned",
        )
        db_session.add(otro)
        db_session.flush()
        db_session.add(
            TripStop(trip_id=otro.id, seq=1, address="Nueva", lat=nueva[0], lng=nueva[1])
        )
        db_session.commit()

    registro = _correr(
        db_session, trip, token, esperas=90, router=RouterRecto(), al_emitir=reemplazar
    )

    despues = [_distancia((lat, lng), nueva) for lat, lng, *_ in registro[cambio - 1 :]]
    llegada = next(i for i, d in enumerate(despues) if d <= RADIO_PARADA_M)
    # Desde el cambio, cada punto queda igual o más cerca de la parada nueva:
    # no termina el tramo hacia la parada 1 del viaje cancelado.
    assert all(b <= a + 0.01 for a, b in pairwise(despues[: llegada + 1]))
    _sin_circuito_ni_saltos(registro)


def test_si_falla_el_ruteo_espera_en_el_lugar_y_retoma_la_ruta(demo, db_session):
    trip, token = demo
    router = RouterRecto(fallas={2})  # cae justo al pedir el tramo a la parada 2

    registro = _correr(db_session, trip, token, esperas=90, router=router)

    estados = [paradas for *_, paradas in registro]
    assert "dpp" in estados  # entregó la 1 y siguió viaje hacia la 2
    assert router.pedidos >= 3
    _sin_circuito_ni_saltos(registro)
