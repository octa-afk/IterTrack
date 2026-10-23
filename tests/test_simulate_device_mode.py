"""Modo dispositivo del simulador: escribe por el mismo camino que un ESP32."""

from datetime import UTC, datetime

import requests

from scripts.simulate_trucks import (
    SIMULATED_DEVICE_PREFIX,
    constructor_de_sender,
    ejecutar_simulaciones,
    enviar_ingesta,
    preparar_dispositivo,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


def device(identifier, device_id, truck_id=None):
    return {
        "id": device_id,
        "identifier": identifier,
        "active": True,
        "organization_id": 7,
        "assignment": {"truck_id": truck_id, "valid_from": "2026-10-23T00:00:00+00:00"}
        if truck_id is not None
        else None,
    }


# ---- transport ----


def test_enviar_ingesta_uses_the_device_bearer_and_batch_payload(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]
        return FakeResponse(payload={"results": [{"sequence": 1, "status": "accepted"}]})

    monkeypatch.setattr("scripts.simulate_trucks.requests.post", fake_post)

    measured_at = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
    assert enviar_ingesta("tok-123", -31.42, -64.18, 35.0, 90.0, measured_at, sequence=7)

    assert captured["url"].endswith("/devices/ingest")
    assert captured["headers"] == {"Authorization": "Bearer tok-123"}
    assert captured["json"]["points"] == [
        {
            "sequence": 7,
            "lat": -31.42,
            "long": -64.18,
            "speed": 35.0,
            "heading": 90.0,
            "recorded_at": "2026-10-23T12:00:00+00:00",
        }
    ]


def test_enviar_ingesta_reports_rejected_points(monkeypatch):
    monkeypatch.setattr(
        "scripts.simulate_trucks.requests.post",
        lambda *a, **k: FakeResponse(payload={"results": [{"sequence": 1, "status": "rejected"}]}),
    )

    assert not enviar_ingesta(
        "tok", 0.0, 0.0, 0.0, 0.0, datetime(2026, 10, 23, tzinfo=UTC)
    )


def test_enviar_ingesta_reports_transport_failure(monkeypatch):
    def explode(*_args, **_kwargs):
        raise requests.ConnectionError("sin red")

    monkeypatch.setattr("scripts.simulate_trucks.requests.post", explode)

    assert not enviar_ingesta(
        "tok", 0.0, 0.0, 0.0, 0.0, datetime(2026, 10, 23, tzinfo=UTC)
    )


def test_constructor_de_sender_increments_the_sequence(monkeypatch):
    sequences = []

    def fake_enviar_ingesta(token, lat, long, speed, heading, recorded_at, sequence=1, batch_id=None):
        sequences.append(sequence)
        return True

    monkeypatch.setattr("scripts.simulate_trucks.enviar_ingesta", fake_enviar_ingesta)

    sender = constructor_de_sender("tok")
    sender(0.0, 0.0, 1.0, 2.0, datetime(2026, 10, 23, tzinfo=UTC))
    sender(0.0, 0.0, 1.0, 2.0, datetime(2026, 10, 23, tzinfo=UTC))

    assert sequences == [1, 2]


# ---- device preparation ----


def test_preparar_dispositivo_provisions_when_none_exists(monkeypatch):
    monkeypatch.setattr("scripts.simulate_trucks.listar_dispositivos", lambda _h: [])
    monkeypatch.setattr("scripts.simulate_trucks._aprovisionar", lambda ident, tid, _h: "fresh-token")

    assert preparar_dispositivo(1, {"Authorization": "Bearer admin"}) == "fresh-token"


def test_preparar_dispositivo_skips_a_truck_held_by_a_real_device(monkeypatch):
    monkeypatch.setattr(
        "scripts.simulate_trucks.listar_dispositivos",
        lambda _h: [device("ESP32-REAL", 5, truck_id=1)],
    )

    revoked = []

    def record_revoke(device_id, _h):
        revoked.append(device_id)
        return True

    monkeypatch.setattr("scripts.simulate_trucks._revocar", record_revoke)

    assert preparar_dispositivo(1, {"Authorization": "Bearer admin"}) is None
    assert revoked == []


def test_preparar_dispositivo_with_force_revokes_the_occupant(monkeypatch):
    rowas = [
        [device("ESP32-REAL", 5, truck_id=1)],
        [device(f"{SIMULATED_DEVICE_PREFIX}-001", 9, truck_id=None)],
    ]
    monkeypatch.setattr(
        "scripts.simulate_trucks.listar_dispositivos", lambda _h: rowas.pop(0) if rowas else []
    )
    revoked = []

    def record_revoke(device_id, _h):
        revoked.append(device_id)
        return True

    monkeypatch.setattr("scripts.simulate_trucks._revocar", record_revoke)
    monkeypatch.setattr("scripts.simulate_trucks._reasignar", lambda *args: True)
    monkeypatch.setattr(
        "scripts.simulate_trucks._rotar_token", lambda device_id, _h: "rotated-token"
    )

    assert preparar_dispositivo(1, {"Authorization": "Bearer admin"}, force=True) == "rotated-token"
    assert revoked == [5]


def test_preparar_dispositivo_reuses_and_rotates_its_own_device(monkeypatch):
    monkeypatch.setattr(
        "scripts.simulate_trucks.listar_dispositivos",
        lambda _h: [device(f"{SIMULATED_DEVICE_PREFIX}-001", 9, truck_id=1)],
    )
    monkeypatch.setattr(
        "scripts.simulate_trucks._rotar_token", lambda device_id, _h: "rotated-token"
    )

    assert preparar_dispositivo(1, {"Authorization": "Bearer admin"}) == "rotated-token"


# ---- orchestration ----


def test_ejecutar_simulaciones_device_mode_skips_occupied_trucks(monkeypatch):
    simulated = []

    class StopImmediately:
        def __init__(self):
            self.stopped = False

        def is_set(self):
            return self.stopped

        def wait(self, _interval):
            self.stopped = True

        def set(self):
            self.stopped = True

    class Completed:
        def result(self):
            return None

    class SynchronousExecutor:
        def __init__(self, max_workers):
            pass

        def submit(self, worker, *args, **kwargs):
            simulated.append(kwargs.get("sender"))
            return Completed()

        def shutdown(self, **kwargs):
            pass

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: [(-31.42, -64.18)])
    monkeypatch.setattr("scripts.simulate_trucks.autenticar_admin", lambda: {"Authorization": "Bearer admin"})
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", lambda *a, **k: None)
    monkeypatch.setattr(
        "scripts.simulate_trucks.preparar_dispositivo",
        lambda truck_id, _h, force=False: None if truck_id == 2 else "token",
    )
    monkeypatch.setattr("scripts.simulate_trucks.Event", StopImmediately)
    monkeypatch.setattr("scripts.simulate_trucks.ThreadPoolExecutor", SynchronousExecutor)

    ejecutar_simulaciones(
        base_id=1, base_plate="ABC123", intervalo=1, count=3, mode="device"
    )

    # Only trucks 1 and 3 got a sender; truck 2 stayed with its real device.
    assert len(simulated) == 2
    assert all(callable(sender) for sender in simulated)


# ---- recuperación del token de dispositivo ----
# Un reset de la demo recrea los dispositivos e invalida sus tokens. Sin
# recuperación, el worker queda en bucle de 401 y el mapa se congela.


def test_enviar_ingesta_retries_once_with_a_renewed_token(monkeypatch):
    enviados = []

    def fake_post(url, **kwargs):
        enviados.append(kwargs["headers"]["Authorization"])
        if len(enviados) == 1:
            return FakeResponse(status_code=401, text='{"detail":"Invalid device credentials"}')
        return FakeResponse(payload={"results": [{"sequence": 1, "status": "accepted"}]})

    monkeypatch.setattr("scripts.simulate_trucks.requests.post", fake_post)

    ok = enviar_ingesta(
        "viejo",
        -31.42,
        -64.18,
        35.0,
        90.0,
        datetime(2026, 10, 23, 12, 0, tzinfo=UTC),
        on_unauthorized=lambda: "nuevo",
    )

    assert ok
    assert enviados == ["Bearer viejo", "Bearer nuevo"]


def test_enviar_ingesta_without_callback_does_not_retry(monkeypatch):
    intentos = []

    def fake_post(url, **kwargs):
        intentos.append(1)
        return FakeResponse(status_code=401, text="no autorizado")

    monkeypatch.setattr("scripts.simulate_trucks.requests.post", fake_post)

    assert not enviar_ingesta(
        "tok", 0.0, 0.0, 0.0, 0.0, datetime(2026, 10, 23, tzinfo=UTC)
    )
    assert len(intentos) == 1


def test_enviar_ingesta_gives_up_when_recovery_yields_no_token(monkeypatch):
    intentos = []

    def fake_post(url, **kwargs):
        intentos.append(1)
        return FakeResponse(status_code=401, text="no autorizado")

    monkeypatch.setattr("scripts.simulate_trucks.requests.post", fake_post)

    assert not enviar_ingesta(
        "tok",
        0.0,
        0.0,
        0.0,
        0.0,
        datetime(2026, 10, 23, tzinfo=UTC),
        on_unauthorized=lambda: None,
    )
    assert len(intentos) == 1


def test_constructor_de_sender_keeps_the_renewed_token(monkeypatch):
    enviados = []

    def fake_enviar_ingesta(
        token, lat, long, speed, heading, recorded_at, sequence=1, batch_id=None,
        on_unauthorized=None,
    ):
        enviados.append(token)
        if token == "viejo" and on_unauthorized is not None:
            on_unauthorized()
        return True

    monkeypatch.setattr("scripts.simulate_trucks.enviar_ingesta", fake_enviar_ingesta)

    sender = constructor_de_sender("viejo", on_unauthorized=lambda: "nuevo")
    sender(0.0, 0.0, 1.0, 2.0, datetime(2026, 10, 23, tzinfo=UTC))
    sender(0.0, 0.0, 1.0, 2.0, datetime(2026, 10, 23, tzinfo=UTC))

    assert enviados == ["viejo", "nuevo"]


def test_constructor_de_sender_rate_limits_a_failing_recovery(monkeypatch):
    intentos = []

    def fake_enviar_ingesta(
        token, lat, long, speed, heading, recorded_at, sequence=1, batch_id=None,
        on_unauthorized=None,
    ):
        if on_unauthorized is not None:
            on_unauthorized()
        return False

    monkeypatch.setattr("scripts.simulate_trucks.enviar_ingesta", fake_enviar_ingesta)

    sender = constructor_de_sender("viejo", on_unauthorized=lambda: intentos.append(1))
    sender(0.0, 0.0, 1.0, 2.0, datetime(2026, 10, 23, tzinfo=UTC))
    sender(0.0, 0.0, 1.0, 2.0, datetime(2026, 10, 23, tzinfo=UTC))

    # Una recuperación fallida no debe golpear la API en cada punto.
    assert len(intentos) == 1
