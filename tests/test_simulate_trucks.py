import os
from datetime import UTC, datetime, timedelta

from scripts.simulate_trucks import (
    actualizar_ubicacion,
    build_truck_configs,
    cargar_env_local,
    ejecutar_simulaciones,
    rotate_route,
    route_offset,
    simular_ruta,
)


def test_actualizar_ubicacion_sends_telemetry(monkeypatch):
    captured = {}

    class Response:
        status_code = 200

    def fake_put(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("scripts.simulate_trucks.requests.put", fake_put)

    measured_at = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)

    assert actualizar_ubicacion(
        7, -31.42, -64.18, speed=35.5, heading=123.4, recorded_at=measured_at, headers={"X-Test": "yes"}
    )
    assert captured["json"] == {
        "lat": -31.42,
        "long": -64.18,
        "speed": 35.5,
        "heading": 123.4,
        "recorded_at": "2026-10-13T12:00:00+00:00",
    }


def test_simular_ruta_captures_measurement_time_for_each_ping(monkeypatch):
    route = [[-31.42, -64.18], [-31.43, -64.19]]
    measurements = []

    class StopAfterRoute:
        def __init__(self):
            self.waits = 0
            self.stopped = False

        def is_set(self):
            return self.stopped

        def wait(self, timeout: float | None = None) -> bool:
            self.waits += 1
            if self.waits == len(route):
                self.stopped = True
            return self.stopped

    def record_measurement(truck_id, lat, long, speed, heading, recorded_at, headers=None):
        measurements.append(recorded_at)
        return True

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: route)
    monkeypatch.setattr("scripts.simulate_trucks.autenticar", dict)
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", lambda *args, **kwargs: None)
    monkeypatch.setattr("scripts.simulate_trucks.actualizar_ubicacion", record_measurement)

    before = datetime.now(UTC)
    simular_ruta(7, "ABC123", 1, stop_event=StopAfterRoute())

    assert len(measurements) == len(route)
    assert all(m.tzinfo is not None for m in measurements)
    assert all(before <= m <= datetime.now(UTC) + timedelta(seconds=1) for m in measurements)


def test_build_truck_configs_preserves_base_identity_for_single_truck():
    configs = build_truck_configs(base_id=7, base_plate="ABC123", count=1)

    assert [(config.truck_id, config.plate) for config in configs] == [(7, "ABC123")]


def test_build_truck_configs_generates_deterministic_unique_identities():
    configs = build_truck_configs(
        base_id=7,
        base_plate="ABC123",
        count=3,
        route_length=12,
    )

    assert [(config.truck_id, config.plate) for config in configs] == [
        (7, "ABC123-01"),
        (8, "ABC123-02"),
        (9, "ABC123-03"),
    ]
    assert [config.route_offset for config in configs] == [0, 4, 8]


def test_route_offsets_are_evenly_spaced_when_route_has_enough_points():
    offsets = [route_offset(route_length=12, truck_index=index, truck_count=3) for index in range(3)]

    assert offsets == [0, 4, 8]
    assert [rotate_route(list(range(12)), offset)[0] for offset in offsets] == [0, 4, 8]


def test_route_offsets_remain_valid_when_more_trucks_than_route_points():
    offsets = [route_offset(route_length=3, truck_index=index, truck_count=5) for index in range(5)]

    assert offsets == [0, 1, 2, 0, 1]


def test_simular_ruta_preserves_history_across_route_laps_by_default(monkeypatch):
    route = [[-31.42, -64.18], [-31.43, -64.19]]
    deleted_trucks = []
    updates = []

    class StopAfterRouteLaps:
        def __init__(self):
            self.waits = 0
            self.stopped = False

        def is_set(self):
            return self.stopped

        def wait(self, timeout: float | None = None) -> bool:
            self.waits += 1
            if self.waits == len(route) * 2:
                self.stopped = True
            return self.stopped

    def record_update(truck_id, *args, **kwargs):
        updates.append(truck_id)
        return True

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: route)
    monkeypatch.setattr("scripts.simulate_trucks.autenticar", dict)
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "scripts.simulate_trucks.limpiar_recorrido",
        lambda truck_id, headers=None: deleted_trucks.append(truck_id),
    )
    monkeypatch.setattr("scripts.simulate_trucks.actualizar_ubicacion", record_update)

    simular_ruta(7, "ABC123", 1, stop_event=StopAfterRouteLaps())

    assert len(updates) == len(route) * 2
    assert deleted_trucks == []


def test_ejecutar_simulaciones_clears_history_once_per_truck_when_requested(monkeypatch):
    route = [[-31.42, -64.18]]
    deleted_trucks = []

    class StopAfterFirstUpdate:
        def __init__(self):
            self.stopped = False

        def is_set(self):
            return self.stopped

        def wait(self, _interval):
            self.stopped = True

        def set(self):
            self.stopped = True

    class CompletedWorker:
        def result(self):
            return None

    class SynchronousExecutor:
        def __init__(self, max_workers):
            assert max_workers == 3

        def submit(self, worker, *args, **kwargs):
            worker(*args, **kwargs)
            return CompletedWorker()

        def shutdown(self, **kwargs):
            pass

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: route)
    monkeypatch.setattr("scripts.simulate_trucks.autenticar", lambda: {"Authorization": "Bearer test"})
    monkeypatch.setattr("scripts.simulate_trucks.autenticar_admin", dict)
    monkeypatch.setattr("scripts.simulate_trucks.Event", StopAfterFirstUpdate)
    monkeypatch.setattr("scripts.simulate_trucks.ThreadPoolExecutor", SynchronousExecutor)
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "scripts.simulate_trucks.limpiar_recorrido",
        lambda truck_id, headers=None: deleted_trucks.append(truck_id),
    )
    monkeypatch.setattr(
        "scripts.simulate_trucks.actualizar_ubicacion",
        lambda *args, **kwargs: True,
    )

    ejecutar_simulaciones(
        base_id=7,
        base_plate="ABC123",
        intervalo=1,
        count=3,
        clear_history_on_start=True,
    )

    assert deleted_trucks == [7, 8, 9]


def test_simular_ruta_uses_admin_headers_only_for_registration(monkeypatch):
    route = [[-31.42, -64.18]]
    seen: dict[str, dict[str, str] | None] = {}

    class StopAfterFirstUpdate:
        def __init__(self):
            self.stopped = False

        def is_set(self):
            return self.stopped

        def wait(self, timeout: float | None = None) -> bool:
            self.stopped = True
            return self.stopped

        def set(self):
            self.stopped = True

    def record_registration(_truck_id, *args, **kwargs):
        seen["registration_headers"] = kwargs.get("headers")

    def record_update(_truck_id, *args, **kwargs):
        seen["update_headers"] = kwargs.get("headers")
        return True

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: route)
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", record_registration)
    monkeypatch.setattr("scripts.simulate_trucks.actualizar_ubicacion", record_update)

    admin_headers = {"Authorization": "Bearer admin"}
    telemetry_headers = {"Authorization": "Bearer telemetry"}

    simular_ruta(
        7,
        "ABC123",
        1,
        headers=telemetry_headers,
        admin_headers=admin_headers,
        stop_event=StopAfterFirstUpdate(),
    )

    assert seen["registration_headers"] == admin_headers
    assert seen["update_headers"] == telemetry_headers


def test_ejecutar_simulaciones_uses_admin_credentials_for_registration(monkeypatch):
    route = [[-31.42, -64.18]]
    seen: dict[str, list[dict[str, str] | None]] = {"registration": [], "update": []}

    class StopAfterFirstUpdate:
        def __init__(self):
            self.stopped = False

        def is_set(self):
            return self.stopped

        def wait(self, timeout: float | None = None) -> bool:
            self.stopped = True
            return self.stopped

        def set(self):
            self.stopped = True

    class CompletedWorker:
        def result(self):
            return None

    class SynchronousExecutor:
        def __init__(self, max_workers):
            assert max_workers == 1

        def submit(self, worker, *args, **kwargs):
            worker(*args, **kwargs)
            return CompletedWorker()

        def shutdown(self, **kwargs):
            pass

    def record_registration(_truck_id, *args, **kwargs):
        seen["registration"].append(kwargs.get("headers"))

    def record_update(_truck_id, *args, **kwargs):
        seen["update"].append(kwargs.get("headers"))
        return True

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: route)
    monkeypatch.setattr(
        "scripts.simulate_trucks.autenticar", lambda: {"Authorization": "Bearer telemetry"}
    )
    monkeypatch.setattr(
        "scripts.simulate_trucks.autenticar_admin", lambda: {"Authorization": "Bearer admin"}
    )
    monkeypatch.setattr("scripts.simulate_trucks.Event", StopAfterFirstUpdate)
    monkeypatch.setattr("scripts.simulate_trucks.ThreadPoolExecutor", SynchronousExecutor)
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", record_registration)
    monkeypatch.setattr("scripts.simulate_trucks.actualizar_ubicacion", record_update)

    ejecutar_simulaciones(base_id=7, base_plate="ABC123", intervalo=1, count=1)

    assert seen["registration"] == [{"Authorization": "Bearer admin"}]
    assert seen["update"] == [{"Authorization": "Bearer telemetry"}]


def test_ejecutar_simulaciones_falls_back_to_telemetry_credentials_for_registration(monkeypatch):
    route = [[-31.42, -64.18]]
    seen: dict[str, list[dict[str, str] | None]] = {"registration": [], "update": []}

    class StopAfterFirstUpdate:
        def __init__(self):
            self.stopped = False

        def is_set(self):
            return self.stopped

        def wait(self, timeout: float | None = None) -> bool:
            self.stopped = True
            return self.stopped

        def set(self):
            self.stopped = True

    class CompletedWorker:
        def result(self):
            return None

    class SynchronousExecutor:
        def __init__(self, max_workers):
            assert max_workers == 1

        def submit(self, worker, *args, **kwargs):
            worker(*args, **kwargs)
            return CompletedWorker()

        def shutdown(self, **kwargs):
            pass

    telemetry_headers = {"Authorization": "Bearer telemetry"}

    def record_registration(_truck_id, *args, **kwargs):
        seen["registration"].append(kwargs.get("headers"))

    def record_update(_truck_id, *args, **kwargs):
        seen["update"].append(kwargs.get("headers"))
        return True

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: route)
    monkeypatch.setattr("scripts.simulate_trucks.autenticar", lambda: dict(telemetry_headers))
    monkeypatch.setattr("scripts.simulate_trucks.autenticar_admin", dict)
    monkeypatch.setattr("scripts.simulate_trucks.Event", StopAfterFirstUpdate)
    monkeypatch.setattr("scripts.simulate_trucks.ThreadPoolExecutor", SynchronousExecutor)
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", record_registration)
    monkeypatch.setattr("scripts.simulate_trucks.actualizar_ubicacion", record_update)

    ejecutar_simulaciones(base_id=7, base_plate="ABC123", intervalo=1, count=1)

    assert seen["registration"] == [telemetry_headers]
    assert seen["update"] == [telemetry_headers]


def test_ejecutar_simulaciones_aborts_without_token(monkeypatch):
    calls = []

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: [(0, 0), (1, 1)])
    monkeypatch.setattr("scripts.simulate_trucks.autenticar", dict)
    monkeypatch.setattr(
        "scripts.simulate_trucks.registrar_camion", lambda *args, **kwargs: calls.append("registrar")
    )
    monkeypatch.setattr(
        "scripts.simulate_trucks.actualizar_ubicacion", lambda *args, **kwargs: calls.append("actualizar")
    )

    ejecutar_simulaciones(base_id=1, base_plate="ABC123", intervalo=1, count=1)

    assert calls == []


class _FakeResponse:
    """Minimal `requests.Response` stand-in with a configurable status code."""

    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_actualizar_ubicacion_renews_token_once_on_unauthorized(monkeypatch):
    seen_headers = []
    responses = [_FakeResponse(401), _FakeResponse(200)]

    def fake_put(_url, **kwargs):
        seen_headers.append(kwargs["headers"])
        return responses.pop(0)

    monkeypatch.setattr("scripts.simulate_trucks.requests.put", fake_put)

    stale = {"Authorization": "Bearer stale"}
    fresh = {"Authorization": "Bearer fresh"}

    assert actualizar_ubicacion(
        7,
        -31.42,
        -64.18,
        speed=10,
        heading=90,
        recorded_at=datetime(2026, 10, 13, 12, 0, tzinfo=UTC),
        headers=stale,
        on_unauthorized=lambda: fresh,
    )
    assert seen_headers == [stale, fresh]


def test_actualizar_ubicacion_reports_failure_when_renewed_token_is_rejected(monkeypatch):
    responses = [_FakeResponse(401), _FakeResponse(401)]
    calls = []

    def fake_put(_url, **kwargs):
        calls.append(kwargs["headers"])
        return responses.pop(0)

    monkeypatch.setattr("scripts.simulate_trucks.requests.put", fake_put)

    assert not actualizar_ubicacion(
        7,
        -31.42,
        -64.18,
        speed=10,
        heading=90,
        recorded_at=datetime(2026, 10, 13, 12, 0, tzinfo=UTC),
        headers={"Authorization": "Bearer stale"},
        on_unauthorized=lambda: {"Authorization": "Bearer fresh"},
    )
    assert len(calls) == 2


def test_actualizar_ubicacion_does_not_retry_without_renewal_callback(monkeypatch):
    calls = []

    def fake_put(_url, **kwargs):
        calls.append(kwargs["headers"])
        return _FakeResponse(401)

    monkeypatch.setattr("scripts.simulate_trucks.requests.put", fake_put)

    assert not actualizar_ubicacion(
        7,
        -31.42,
        -64.18,
        speed=10,
        heading=90,
        recorded_at=datetime(2026, 10, 13, 12, 0, tzinfo=UTC),
        headers={"Authorization": "Bearer stale"},
    )
    assert len(calls) == 1


def test_simular_ruta_propagates_renewed_headers_to_the_shared_dict(monkeypatch):
    route = [[-31.42, -64.18], [-31.43, -64.19]]
    shared_headers = {"Authorization": "Bearer stale"}
    seen = []
    renewed_once = {"done": False}

    class StopAfterRoute:
        def __init__(self):
            self.waits = 0
            self.stopped = False

        def is_set(self):
            return self.stopped

        def wait(self, timeout: float | None = None) -> bool:
            self.waits += 1
            if self.waits >= len(route):
                self.stopped = True
            return self.stopped

    def fake_update(_truck_id, *_args, **kwargs):
        seen.append(dict(kwargs["headers"]))
        if not renewed_once["done"]:
            renewed_once["done"] = True
            kwargs["on_unauthorized"]()
        return True

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: route)
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", lambda *args, **kwargs: None)
    monkeypatch.setattr("scripts.simulate_trucks.actualizar_ubicacion", fake_update)

    simular_ruta(
        7,
        "ABC123",
        1,
        headers=shared_headers,
        stop_event=StopAfterRoute(),
        refresh_headers=lambda: {"Authorization": "Bearer fresh"},
    )

    assert seen[0] == {"Authorization": "Bearer stale"}
    assert seen[-1] == {"Authorization": "Bearer fresh"}
    assert shared_headers == {"Authorization": "Bearer fresh"}


def test_cargar_env_local_loads_values_without_overriding_process_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ITERTRACK_PROBE_KEEP=from_file\nITERTRACK_PROBE_NEW=from_file\n")

    monkeypatch.setenv("ITERTRACK_PROBE_KEEP", "from_process")
    monkeypatch.delenv("ITERTRACK_PROBE_NEW", raising=False)

    cargar_env_local(env_file)

    assert os.environ["ITERTRACK_PROBE_KEEP"] == "from_process"
    assert os.environ["ITERTRACK_PROBE_NEW"] == "from_file"

    monkeypatch.delenv("ITERTRACK_PROBE_NEW", raising=False)

