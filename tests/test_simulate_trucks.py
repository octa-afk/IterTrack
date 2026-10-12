from scripts.simulate_trucks import (
    actualizar_ubicacion,
    build_truck_configs,
    ejecutar_simulaciones,
    route_offset,
    rotate_route,
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

    assert actualizar_ubicacion(7, -31.42, -64.18, speed=35.5, heading=123.4, headers={"X-Test": "yes"})
    assert captured["json"] == {
        "lat": -31.42,
        "long": -64.18,
        "speed": 35.5,
        "heading": 123.4,
    }


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

        def wait(self, _interval):
            self.waits += 1
            if self.waits == len(route) * 2:
                self.stopped = True

    monkeypatch.setattr("scripts.simulate_trucks.cargar_ruta", lambda: route)
    monkeypatch.setattr("scripts.simulate_trucks.autenticar", lambda: {})
    monkeypatch.setattr("scripts.simulate_trucks.registrar_camion", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "scripts.simulate_trucks.limpiar_recorrido",
        lambda truck_id, headers=None: deleted_trucks.append(truck_id),
    )
    monkeypatch.setattr(
        "scripts.simulate_trucks.actualizar_ubicacion",
        lambda truck_id, *args, **kwargs: updates.append(truck_id) or True,
    )

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
    monkeypatch.setattr("scripts.simulate_trucks.autenticar", lambda: {})
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
