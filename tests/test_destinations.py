"""Dadores de carga, viajes y resolución de direcciones.

El geocoder se inyecta como dependencia: estos tests le pasan un doble y nunca
salen a la red. Lo que se verifica es el pipeline —caché, procedencia, cola de
pendientes y aislamiento por organización—, no la calidad de un proveedor.
"""

import pytest

from source.main import app
from source.models.destination import AddressCache, Charger
from source.services.auth import get_current_user
from source.services.geocoding import GeoResult, get_geocoder, normalize_address


class FakeGeocoder:
    name = "fake"

    def __init__(self, results=None):
        # address -> (lat, lng) o None para simular "no encontrada"
        self.results = results or {}
        self.calls: list[str] = []

    def geocode(self, address):
        self.calls.append(address)
        coords = self.results.get(address)
        if coords is None:
            return None
        return GeoResult(lat=coords[0], lng=coords[1], provider=self.name, confidence=0.9)


@pytest.fixture()
def usar_geocoder():
    """Instala el doble como dependencia y lo devuelve."""

    def _install(results=None):
        fake = FakeGeocoder(results)
        app.dependency_overrides[get_geocoder] = lambda: fake
        return fake

    yield _install
    app.dependency_overrides.pop(get_geocoder, None)


def _stop(address, **extra):
    return {"address": address, **extra}


def _trip_payload(charger_id, stops, **extra):
    return {
        "charger_id": charger_id,
        "departure_at": "2026-10-25T07:30:00-03:00",
        "stops": stops,
        **extra,
    }


@pytest.fixture()
def charger(db_session, test_org):
    item = Charger(organization_id=test_org.id, name="Colchones Sur")
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_crear_y_listar_dadores_de_carga(admin_client, test_org):
    creado = admin_client.post("/chargers", json={"name": "Colchones Sur"})
    assert creado.status_code == 201
    assert creado.json()["name"] == "Colchones Sur"

    listado = admin_client.get("/chargers")
    assert listado.status_code == 200
    assert [c["name"] for c in listado.json()] == ["Colchones Sur"]


def test_dador_de_carga_duplicado_responde_400(admin_client, test_org):
    assert admin_client.post("/chargers", json={"name": "Colchones Sur"}).status_code == 201
    repetido = admin_client.post("/chargers", json={"name": "Colchones Sur"})
    assert repetido.status_code == 400


def test_importar_viaje_resuelve_destinos_y_puebla_la_cache(
    admin_client, charger, db_session, usar_geocoder
):
    usar_geocoder({"Av. Colón 1234, Córdoba": (-31.4135, -64.1811)})

    response = admin_client.post(
        "/trips",
        json=_trip_payload(
            charger.id,
            [
                _stop("Av. Colón 1234, Córdoba", receiver="Depósito Norte"),
                _stop("Ruta 9 km 720"),
            ],
        ),
    )

    assert response.status_code == 201, response.text
    stops = response.json()["stops"]
    assert [s["seq"] for s in stops] == [1, 2]

    resuelto, pendiente = stops
    assert (resuelto["lat"], resuelto["lng"]) == (-31.4135, -64.1811)
    assert resuelto["geo_source"] == "fake"
    assert resuelto["needs_review"] is False
    # Lo que el geocoder no encuentra no se inventa: queda en la cola.
    assert pendiente["lat"] is None
    assert pendiente["needs_review"] is True

    cache = db_session.query(AddressCache).one()
    assert cache.address_norm == normalize_address("Av. Colón 1234, Córdoba")
    assert cache.provider == "fake"


def test_reimportar_la_misma_direccion_no_vuelve_a_geocodificar(
    admin_client, charger, usar_geocoder
):
    fake = usar_geocoder({"Av. Colón 1234, Córdoba": (-31.4135, -64.1811)})
    payload = _trip_payload(charger.id, [_stop("Av. Colón 1234, Córdoba")])

    assert admin_client.post("/trips", json=payload).status_code == 201
    # La segunda vez la dirección viene escrita distinto: sin normalizar, sería
    # otra consulta al proveedor.
    payload["stops"] = [_stop("AV COLON 1234, cordoba")]
    segundo = admin_client.post("/trips", json=payload)

    assert segundo.status_code == 201
    assert segundo.json()["stops"][0]["geo_source"] == "cache"
    assert fake.calls == ["Av. Colón 1234, Córdoba"]


def test_coordenadas_provistas_por_el_dador_no_llaman_al_geocoder(
    admin_client, charger, usar_geocoder
):
    fake = usar_geocoder()

    response = admin_client.post(
        "/trips",
        json=_trip_payload(
            charger.id,
            [_stop("Planta Villa María", lat=-32.4075, lng=-63.2401)],
        ),
    )

    assert response.status_code == 201
    stop = response.json()["stops"][0]
    assert stop["geo_source"] == "provided"
    assert stop["needs_review"] is False
    assert fake.calls == []


def test_referencia_externa_repetida_responde_409(admin_client, charger, usar_geocoder):
    usar_geocoder()
    payload = _trip_payload(
        charger.id, [_stop("Av. Colón 1234")], external_ref="ENVIO-001"
    )
    assert admin_client.post("/trips", json=payload).status_code == 201
    assert admin_client.post("/trips", json=payload).status_code == 409


def test_pin_manual_resuelve_el_destino_y_lo_deja_en_cache(
    admin_client, charger, db_session, usar_geocoder
):
    fake = usar_geocoder()
    creado = admin_client.post(
        "/trips", json=_trip_payload(charger.id, [_stop("Ruta 9 km 720")])
    )
    trip_id = creado.json()["id"]
    stop_id = creado.json()["stops"][0]["id"]
    assert admin_client.get("/destinations/pending").json()[0]["id"] == stop_id

    resuelto = admin_client.patch(
        f"/trips/{trip_id}/stops/{stop_id}", json={"lat": -31.5, "lng": -64.2}
    )
    assert resuelto.status_code == 200
    assert resuelto.json()["geo_source"] == "manual"
    assert resuelto.json()["needs_review"] is False
    assert admin_client.get("/destinations/pending").json() == []

    # El pin manual entrena la caché: la próxima importación no consulta.
    fake.calls.clear()
    admin_client.post("/trips", json=_trip_payload(charger.id, [_stop("RUTA 9 KM 720")]))
    assert fake.calls == []
    assert db_session.query(AddressCache).one().provider == "manual"


def test_viaje_de_otra_organizacion_responde_404(
    admin_client, db_session, test_org2, usar_geocoder
):
    usar_geocoder()
    ajeno = Charger(organization_id=test_org2.id, name="Otra empresa")
    db_session.add(ajeno)
    db_session.commit()

    response = admin_client.post(
        "/trips", json=_trip_payload(ajeno.id, [_stop("Av. Colón 1234")])
    )
    assert response.status_code == 404


def test_member_no_puede_importar_viajes(client, test_user, test_org, db_session):
    app.dependency_overrides[get_current_user] = lambda: test_user
    charger = Charger(organization_id=test_org.id, name="Colchones Sur")
    db_session.add(charger)
    db_session.commit()

    response = client.post("/trips", json=_trip_payload(charger.id, [_stop("Av. Colón 1234")]))
    assert response.status_code == 403


def test_normalize_address_ignora_acentos_mayusculas_y_puntuacion():
    assert normalize_address("Av. Colón 1234, Córdoba") == "av colon 1234 cordoba"
    assert normalize_address("  AV   COLON 1234 cordoba ") == "av colon 1234 cordoba"


def test_salida_sin_zona_horaria_responde_422(admin_client, charger, usar_geocoder):
    usar_geocoder()
    payload = _trip_payload(charger.id, [_stop("Av. Colón 1234")])
    payload["departure_at"] = "2026-10-25T07:30:00"
    assert admin_client.post("/trips", json=payload).status_code == 422


def test_el_unico_deposito_de_la_organizacion_se_usa_sin_elegirlo(
    admin_client, charger, usar_geocoder
):
    usar_geocoder({"Av. Colón 1234": (-31.4135, -64.1811)})
    depot = admin_client.post(
        "/depots",
        json={"name": "Depósito Centro", "lat": -31.4135, "lng": -64.1811},
    )
    assert depot.status_code == 201

    creado = admin_client.post(
        "/trips", json=_trip_payload(charger.id, [_stop("Av. Colón 1234")])
    )
    assert creado.status_code == 201
    assert creado.json()["depot_id"] == depot.json()["id"]


def test_deposito_de_otra_organizacion_no_se_puede_usar(
    admin_client, charger, db_session, test_org2, usar_geocoder
):
    from source.models.destination import Depot

    usar_geocoder()
    ajeno = Depot(organization_id=test_org2.id, name="Ajeno", lat=-31.4, lng=-64.1)
    db_session.add(ajeno)
    db_session.commit()

    payload = _trip_payload(charger.id, [_stop("Av. Colón 1234")], depot_id=ajeno.id)
    assert admin_client.post("/trips", json=payload).status_code == 404


def test_camiones_disponibles_excluye_los_que_tienen_viaje_abierto(
    admin_client, charger, db_session, test_truck, usar_geocoder
):
    from source.models.truck import Truck

    usar_geocoder({"Av. Colón 1234": (-31.4135, -64.1811), "Ruta 9": (-31.5, -64.2)})
    libre = Truck(id=2, plate="LIBRE2", organization_id=test_truck.organization_id)
    db_session.add(libre)
    db_session.commit()

    assert [t["plate"] for t in admin_client.get("/trips/available-trucks").json()] == [
        "LIBRE2",
        "TEST123",
    ]

    admin_client.post(
        "/trips",
        json=_trip_payload(charger.id, [_stop("Av. Colón 1234")], truck_id=test_truck.id),
    )
    assert [t["plate"] for t in admin_client.get("/trips/available-trucks").json()] == [
        "LIBRE2"
    ]
