import os
from datetime import UTC, datetime, timedelta
from itertools import pairwise

import pytest

from scripts.simulate_trucks import (
    _reaprovisionar_dispositivo,
    build_truck_configs,
    calcular_distancia_metros,
    cargar_env_local,
    cargar_ruta,
    ejecutar_simulaciones,
    espera_y_velocidad,
    rotate_route,
    route_offset,
    simular_ruta,
    truck_plates,
)


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

    def record_measurement(lat, long, speed, heading, recorded_at):
        measurements.append(recorded_at)
        return True

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: route)
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", lambda *args, **kwargs: None)

    before = datetime.now(UTC)
    simular_ruta(7, "ABC123", 1, stop_event=StopAfterRoute(), sender=record_measurement)

    assert len(measurements) == len(route)
    assert all(m.tzinfo is not None for m in measurements)
    assert all(before <= m <= datetime.now(UTC) + timedelta(seconds=1) for m in measurements)


def test_build_truck_configs_preserves_base_identity_for_single_truck():
    configs = build_truck_configs(base_id=7, base_plate="ABC123", count=1)

    assert [(config.truck_id, config.plate) for config in configs] == [(7, "ABC123")]


def test_build_truck_configs_uses_the_configured_plates():
    configs = build_truck_configs(
        base_id=1,
        base_plate="ABC123",
        count=3,
        route_length=12,
        plates=("ABC", "DEF", "XYZ"),
    )

    assert [config.plate for config in configs] == ["ABC", "DEF", "XYZ"]


def test_build_truck_configs_falls_back_when_the_plate_list_is_short():
    configs = build_truck_configs(
        base_id=1,
        base_plate="ABC123",
        count=3,
        plates=("ABC", "DEF"),
    )

    assert [config.plate for config in configs] == ["ABC", "DEF", "ABC123-03"]


def test_truck_plates_defaults_to_distinct_plates(monkeypatch):
    monkeypatch.delenv("TRUCK_PLATES", raising=False)

    assert truck_plates() == ("ABC123", "DEF456", "XYZ789")


def test_truck_plates_reads_the_environment_list(monkeypatch):
    monkeypatch.setenv("TRUCK_PLATES", " aa1 , bb2 ,,")

    assert truck_plates() == ("AA1", "BB2")


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

    def record_send(*_args, **_kwargs):
        updates.append(1)
        return True

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: route)
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "scripts.simulate_trucks.limpiar_recorrido",
        lambda truck_id, headers=None: deleted_trucks.append(truck_id),
    )

    simular_ruta(7, "ABC123", 1, stop_event=StopAfterRouteLaps(), sender=record_send)

    assert len(updates) == len(route) * 2
    assert deleted_trucks == []


def test_simular_ruta_requires_a_device_sender():
    """No hay camino alternativo: la telemetría solo la manda un dispositivo."""
    with pytest.raises(ValueError):
        simular_ruta(7, "ABC123", 1)


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
    monkeypatch.setattr(
        "scripts.simulate_trucks.autenticar_admin", lambda: {"Authorization": "Bearer admin"}
    )
    monkeypatch.setattr("scripts.simulate_trucks.Event", StopAfterFirstUpdate)
    monkeypatch.setattr("scripts.simulate_trucks.ThreadPoolExecutor", SynchronousExecutor)
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "scripts.simulate_trucks.preparar_dispositivo",
        lambda truck_id, headers=None, force=False: f"tok-{truck_id}",
    )
    monkeypatch.setattr(
        "scripts.simulate_trucks.constructor_de_sender",
        lambda token, on_unauthorized=None: (lambda *args, **kwargs: True),
    )
    monkeypatch.setattr(
        "scripts.simulate_trucks.limpiar_recorrido",
        lambda truck_id, headers=None: deleted_trucks.append(truck_id),
    )

    ejecutar_simulaciones(
        base_id=7,
        base_plate="ABC123",
        intervalo=1,
        count=3,
        clear_history_on_start=True,
    )

    assert deleted_trucks == [7, 8, 9]


def test_ejecutar_simulaciones_registers_with_admin_credentials(monkeypatch):
    route = [[-31.42, -64.18]]
    registrations = []
    provisions = []

    class StopNow:
        def is_set(self):
            return True

        def wait(self, _interval=None):
            return True

        def set(self):
            pass

    class CompletedWorker:
        def result(self):
            return None

    class SynchronousExecutor:
        def __init__(self, max_workers):
            pass

        def submit(self, worker, *args, **kwargs):
            worker(*args, **kwargs)
            return CompletedWorker()

        def shutdown(self, **kwargs):
            pass

    def record_registration(truck_id, plate=None, headers=None, **kwargs):
        registrations.append((truck_id, headers))

    def record_provision(truck_id, headers=None, force=False):
        provisions.append((truck_id, headers))
        return f"tok-{truck_id}"

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: route)
    monkeypatch.setattr(
        "scripts.simulate_trucks.autenticar_admin", lambda: {"Authorization": "Bearer admin"}
    )
    monkeypatch.setattr("scripts.simulate_trucks.Event", StopNow)
    monkeypatch.setattr("scripts.simulate_trucks.ThreadPoolExecutor", SynchronousExecutor)
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", record_registration)
    monkeypatch.setattr("scripts.simulate_trucks.preparar_dispositivo", record_provision)
    monkeypatch.setattr(
        "scripts.simulate_trucks.constructor_de_sender",
        lambda token, on_unauthorized=None: (lambda *args, **kwargs: True),
    )

    ejecutar_simulaciones(base_id=7, base_plate="ABC123", intervalo=1, count=1)

    admin = {"Authorization": "Bearer admin"}
    assert registrations[0] == (7, admin)
    assert all(headers == admin for _, headers in registrations)
    assert provisions == [(7, admin)]


def test_ejecutar_simulaciones_aborts_without_admin_credentials(monkeypatch):
    calls = []

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: [(0, 0), (1, 1)])
    monkeypatch.setattr("scripts.simulate_trucks.autenticar_admin", dict)
    monkeypatch.setattr(
        "scripts.simulate_trucks.registrar_camion", lambda *args, **kwargs: calls.append("registrar")
    )
    monkeypatch.setattr(
        "scripts.simulate_trucks.preparar_dispositivo", lambda *args, **kwargs: calls.append("preparar")
    )

    # A container must exit non-zero here, otherwise the orchestrator treats
    # the run as successful and stops restarting it.
    assert ejecutar_simulaciones(base_id=1, base_plate="ABC123", intervalo=1, count=1) is False

    assert calls == []


class _FakeResponse:
    """Minimal `requests.Response` stand-in with a configurable status code."""

    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}
        self._payload = payload or {}

    def json(self):
        return self._payload






def test_cargar_env_local_loads_values_without_overriding_process_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ITERTRACK_PROBE_KEEP=from_file\nITERTRACK_PROBE_NEW=from_file\n")

    monkeypatch.setenv("ITERTRACK_PROBE_KEEP", "from_process")
    monkeypatch.delenv("ITERTRACK_PROBE_NEW", raising=False)

    cargar_env_local(env_file)

    assert os.environ["ITERTRACK_PROBE_KEEP"] == "from_process"
    assert os.environ["ITERTRACK_PROBE_NEW"] == "from_file"

    monkeypatch.delenv("ITERTRACK_PROBE_NEW", raising=False)



# ---- cadencia y velocidad realista ----
# La ruta no tiene espaciado uniforme: a un punto cada 2 s fijos, un tramo de
# 162 m implica 293 km/h y el panel dibuja un límite de 90 km/h.


def test_espera_y_velocidad_caps_a_long_segment_at_the_target_speed():
    espera, velocidad = espera_y_velocidad(160.0, intervalo_minimo=2.0, objetivo_kmh=55.0)

    assert velocidad == pytest.approx(55.0, abs=0.01)
    assert espera == pytest.approx(160.0 / (55.0 / 3.6), abs=0.01)


def test_espera_y_velocidad_keeps_the_minimum_interval_on_short_segments():
    espera, velocidad = espera_y_velocidad(2.0, intervalo_minimo=2.0, objetivo_kmh=55.0)

    assert espera == 2.0
    assert velocidad == pytest.approx(3.6, abs=0.01)


def test_espera_y_velocidad_handles_a_zero_length_segment():
    espera, velocidad = espera_y_velocidad(0.0, intervalo_minimo=2.0, objetivo_kmh=55.0)

    assert espera == 2.0
    assert velocidad == 0.0


def test_no_segment_of_the_real_route_exceeds_the_target_speed():
    ruta = cargar_ruta()
    objetivo = 55.0

    velocidades = []
    for (lat1, lon1), (lat2, lon2) in pairwise(ruta):
        dist = calcular_distancia_metros(lat1, lon1, lat2, lon2)
        _, velocidad = espera_y_velocidad(dist, intervalo_minimo=2.0, objetivo_kmh=objetivo)
        velocidades.append(velocidad)

    assert max(velocidades) <= objetivo + 0.01
    assert max(velocidades) < 90


class _RecordingStop:
    """StopSignal que registra cada espera y corta al completar una vuelta."""

    def __init__(self, points: int):
        self.waits: list[float] = []
        self.limit = points
        self.stopped = False

    def is_set(self) -> bool:
        return self.stopped

    def wait(self, timeout: float | None = None) -> bool:
        self.waits.append(timeout or 0.0)
        if len(self.waits) >= self.limit:
            self.stopped = True
        return self.stopped

    def set(self) -> None:
        self.stopped = True


def _run_one_lap(monkeypatch, route, intervalo=2.0):
    """Corre `simular_ruta` una vuelta sin dormir y devuelve las esperas."""
    stop = _RecordingStop(points=len(route))
    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: route)
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", lambda *args, **kwargs: None)
    simular_ruta(7, "ABC123", intervalo, stop_event=stop, sender=lambda *args, **kwargs: True)
    return stop.waits


def test_wait_after_a_point_covers_the_segment_to_the_next_point(monkeypatch):
    """La espera posterior al punto i es la del tramo i -> i+1, no la del anterior.

    Con tramos alternados corto/largo, desplazar la espera un punto hace que un
    tramo de 100 m viaje con el pacing de uno de 30 m (y el panel lo marque en
    alerta por exceso de velocidad).
    """
    route = [
        [-31.400000, -64.180000],  # 0 m
        [-31.400270, -64.180000],  # 30 m
        [-31.401168, -64.180000],  # 130 m desde el anterior
        [-31.401438, -64.180000],  # 30 m
        [-31.400000, -64.180000],  # cierra el circuito: ~160 m
    ]
    waits = _run_one_lap(monkeypatch, route)

    esperadas = []
    for i in range(len(route)):
        siguiente = route[(i + 1) % len(route)]
        dist = calcular_distancia_metros(route[i][0], route[i][1], siguiente[0], siguiente[1])
        esperadas.append(max(2.0, dist / (55.0 / 3.6)))

    assert waits == pytest.approx(esperadas, abs=0.01)


def test_a_simulated_lap_never_exceeds_the_target_speed(monkeypatch):
    """Invariante real: distancia recorrida / espera nunca supera el objetivo."""
    route = cargar_ruta()
    waits = _run_one_lap(monkeypatch, route)

    velocidades = []
    for i in range(len(route)):
        siguiente = route[(i + 1) % len(route)]
        dist = calcular_distancia_metros(route[i][0], route[i][1], siguiente[0], siguiente[1])
        velocidades.append(dist / waits[i] * 3.6)

    assert max(velocidades) <= 55.0 + 0.01


def test_recovery_renews_the_admin_jwt_before_reprovisioning(monkeypatch):
    """El JWT de admin vence en 60 min; sin re-login la recuperación da 401."""
    stale = {"Authorization": "Bearer stale"}
    seen = []

    monkeypatch.setattr(
        "scripts.simulate_trucks.autenticar_admin",
        lambda: {"Authorization": "Bearer fresh"},
    )

    def fake_preparar(truck_id, headers, force=False):
        seen.append((truck_id, dict(headers)))
        return "tok"

    monkeypatch.setattr("scripts.simulate_trucks.preparar_dispositivo", fake_preparar)

    assert _reaprovisionar_dispositivo(3, stale) == "tok"

    assert seen == [(3, {"Authorization": "Bearer fresh"})]
    # El dict es compartido con los demás hilos: se actualiza en el lugar.
    assert stale == {"Authorization": "Bearer fresh"}


def test_device_mode_recovery_reauthenticates_the_admin(monkeypatch):
    """La recuperación que recibe el sender renueva el JWT antes de aprovisionar."""
    logins: list[int] = []
    recoveries = []
    headers_seen: list[dict] = []

    class StopNow:
        def is_set(self):
            return True

        def set(self):
            pass

        def wait(self, timeout=None):
            return True

    class Completed:
        def result(self):
            return None

    class SyncExecutor:
        def __init__(self, max_workers):
            pass

        def submit(self, worker, *args, **kwargs):
            worker(*args, **kwargs)
            return Completed()

        def shutdown(self, **kwargs):
            pass

    def fake_admin_login():
        logins.append(len(logins) + 1)
        return {"Authorization": f"Bearer admin-{len(logins)}"}

    def fake_preparar(truck_id, headers=None, force=False):
        headers_seen.append(dict(headers or {}))
        return f"tok-{truck_id}"

    def fake_sender_factory(token, on_unauthorized=None):
        recoveries.append(on_unauthorized)
        return lambda *args, **kwargs: True

    monkeypatch.setattr(
        "scripts.simulate_trucks.cargar_ruta", lambda: [[-31.4, -64.18], [-31.5, -64.19]]
    )
    monkeypatch.setattr("scripts.simulate_trucks.autenticar_admin", fake_admin_login)
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", lambda *args, **kwargs: None)
    monkeypatch.setattr("scripts.simulate_trucks.preparar_dispositivo", fake_preparar)
    monkeypatch.setattr("scripts.simulate_trucks.constructor_de_sender", fake_sender_factory)
    monkeypatch.setattr("scripts.simulate_trucks.Event", StopNow)
    monkeypatch.setattr("scripts.simulate_trucks.ThreadPoolExecutor", SyncExecutor)
    monkeypatch.setattr("scripts.simulate_trucks.simular_ruta", lambda *args, **kwargs: None)

    assert ejecutar_simulaciones(base_id=7, base_plate="ABC123", intervalo=1, count=1)

    assert headers_seen == [{"Authorization": "Bearer admin-1"}]
    assert recoveries[0] is not None

    assert recoveries[0]() == "tok-7"

    assert logins == [1, 2]
    assert headers_seen[-1] == {"Authorization": "Bearer admin-2"}
