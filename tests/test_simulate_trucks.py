from scripts.simulate_trucks import (
    actualizar_ubicacion,
    build_truck_configs,
    route_offset,
    rotate_route,
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
