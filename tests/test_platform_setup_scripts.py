"""Bootstrap de plataforma y seed de demo: separación de tenants y reset seguro."""

from typing import Any

import pytest

from scripts.bootstrap_platform import (
    BootstrapError,
    PlatformBootstrapConfig,
    bootstrap_platform,
)
from scripts.seed_demo import DemoSeedConfig, SeedError, renew_demo_trips, seed_demo
from scripts.simulate_trucks import calcular_distancia_metros
from source.models.destination import Trip
from source.models.device import Device, DeviceAssignment
from source.models.organization import Organization
from source.models.truck import Truck
from source.models.user import ROLE_MEMBER, ROLE_ORG_ADMIN, ROLE_PLATFORM_ADMIN, User

PASSWORD = "supersecret12345"


def platform_config(**overrides: Any) -> PlatformBootstrapConfig:
    data: dict[str, Any] = {
        "org_name": "IterTrack",
        "username": "owner",
        "email": "owner@itertrack.local",
        "full_name": "Platform Owner",
        "password": PASSWORD,
    }
    data.update(overrides)
    return PlatformBootstrapConfig(**data)


def demo_config(**overrides: Any) -> DemoSeedConfig:
    data: dict[str, Any] = {
        "org_name": "Demo Corp",
        "admin_username": "demo-admin",
        "admin_email": "demo-admin@itertrack.local",
        "admin_full_name": "Demo Admin",
        "admin_password": PASSWORD,
        "member_username": "demo",
        "member_email": "demo@itertrack.local",
        "member_full_name": "Demo User",
        "member_password": PASSWORD,
        "truck_count": 3,
        "base_id": 1,
        "base_plate": "ABC123",
        "device_prefix": "SIM",
    }
    data.update(overrides)
    return DemoSeedConfig(**data)


# ---- platform bootstrap ----


def test_bootstrap_creates_internal_organization_and_platform_admin(db_session):
    result = bootstrap_platform(db_session, platform_config())

    assert result.organization_created is True
    assert result.user_created is True

    organization = db_session.query(Organization).filter_by(name="IterTrack").one()
    # The internal organization must never be joinable through an invitation.
    assert organization.invitation_revoked_at is not None

    user = db_session.query(User).filter_by(username="owner").one()
    assert user.role == ROLE_PLATFORM_ADMIN
    assert user.organization_id == organization.id


def test_bootstrap_is_idempotent(db_session):
    bootstrap_platform(db_session, platform_config())
    second = bootstrap_platform(db_session, platform_config())

    assert second.organization_created is False
    assert second.user_created is False
    assert db_session.query(User).filter_by(username="owner").count() == 1
    assert db_session.query(Organization).filter_by(name="IterTrack").count() == 1


def test_bootstrap_promotes_an_existing_user(db_session):
    organization = Organization(name="IterTrack", invitation_code="INTERNAL-CODE")
    db_session.add(organization)
    db_session.commit()
    user = User(
        username="owner",
        email="owner@itertrack.local",
        full_name="Owner",
        hashed_password="x",
        organization_id=organization.id,
        role=ROLE_MEMBER,
    )
    db_session.add(user)
    db_session.commit()

    result = bootstrap_platform(db_session, platform_config())

    assert result.user_created is False
    db_session.refresh(user)
    assert user.role == ROLE_PLATFORM_ADMIN


def test_bootstrap_rejects_short_password(db_session):
    with pytest.raises(BootstrapError):
        bootstrap_platform(db_session, platform_config(password="corta"))


# ---- demo seed ----


def test_seed_creates_demo_tenant_with_its_roles_and_fleet(db_session, monkeypatch):
    monkeypatch.delenv("TRUCK_PLATES", raising=False)
    result = seed_demo(db_session, demo_config())

    organization = db_session.get(Organization, result.organization_id)
    assert organization.name == "Demo Corp"

    admin = db_session.query(User).filter_by(username="demo-admin").one()
    member = db_session.query(User).filter_by(username="demo").one()
    assert admin.role == ROLE_ORG_ADMIN
    assert member.role == ROLE_MEMBER
    assert admin.organization_id == organization.id
    assert member.organization_id == organization.id

    trucks = (
        db_session.query(Truck)
        .filter(Truck.organization_id == organization.id)
        .order_by(Truck.id)
        .all()
    )
    assert [(truck.id, truck.plate) for truck in trucks] == [
        (1, "ABC123"),
        (2, "DEF456"),
        (3, "XYZ789"),
    ]

    devices = db_session.query(Device).filter(Device.identifier.like("SIM-%")).all()
    assert len(devices) == 3
    assert all(device.organization_id == organization.id for device in devices)
    assert (
        db_session.query(DeviceAssignment)
        .filter(DeviceAssignment.valid_to.is_(None))
        .count()
        == 3
    )


def test_seed_converges_plates_when_the_fleet_list_changes(db_session, monkeypatch):
    """Renombrar la flota no puede exigir un reset: el reset borra el historial."""
    seed_demo(db_session, demo_config())

    monkeypatch.setenv("TRUCK_PLATES", "AAA111,BBB222,CCC333")
    again = seed_demo(db_session, demo_config())

    assert again.trucks == 0
    plates = [truck.plate for truck in db_session.query(Truck).order_by(Truck.id)]
    assert plates == ["AAA111", "BBB222", "CCC333"]
    primer_viaje = (
        db_session.query(Trip).filter(Trip.external_ref == "DEMO-001").one()
    )
    assert primer_viaje.stops[0].address.endswith("AAA111")


def test_seed_gives_each_truck_its_own_trip(db_session):
    """Cada camión lleva un viaje propio: si comparten paradas, el mapa muestra
    los mismos destinos para los tres y la sección Rutas no distingue nada."""
    result = seed_demo(db_session, demo_config())

    trips = (
        db_session.query(Trip)
        .filter(Trip.organization_id == result.organization_id)
        .order_by(Trip.external_ref)
        .all()
    )

    assert [trip.external_ref for trip in trips] == ["DEMO-001", "DEMO-002", "DEMO-003"]
    assert [trip.truck_id for trip in trips] == [1, 2, 3]
    assert [trip.status for trip in trips] == ["in_progress", "in_progress", "done"]
    paradas = [(stop.lat, stop.lng) for trip in trips for stop in trip.stops]
    assert len(paradas) == 9
    assert len(set(paradas)) == 9
    assert all(
        stop.geo_source == "provided" and stop.needs_review is False
        for trip in trips
        for stop in trip.stops
    )
    # Cada viaje sale de un circuito propio: si compartieran ruta, las primeras
    # paradas caerían a metros unas de otras.
    primeros = {trip.truck_id: (trip.stops[0].lat, trip.stops[0].lng) for trip in trips}
    for left in (1, 2, 3):
        for right in (1, 2, 3):
            if left < right:
                assert calcular_distancia_metros(*primeros[left], *primeros[right]) > 2000


def test_seed_rebuilds_demo_trip_stops_that_went_stale(db_session):
    """El seed es dueño de los viajes DEMO-*: si la ruta cambia, reescribe sus
    paradas en vez de dejar coordenadas de una corrida anterior."""
    seed_demo(db_session, demo_config())
    trip = db_session.query(Trip).filter(Trip.external_ref == "DEMO-001").one()
    original = trip.stops[0].lat
    trip.stops[0].lat = 0.0
    db_session.commit()

    result = seed_demo(db_session, demo_config())

    assert result.trips == 0
    assert result.trips_rebuilt == 1
    db_session.refresh(trip)
    assert trip.stops[0].lat == original


def test_seed_is_idempotent_without_reset(db_session):
    seed_demo(db_session, demo_config())
    result = seed_demo(db_session, demo_config())

    assert result.trucks == 0
    assert result.devices == 0
    organization = db_session.get(Organization, result.organization_id)
    assert db_session.query(Truck).filter(Truck.organization_id == organization.id).count() == 3
    assert db_session.query(User).filter(User.organization_id == organization.id).count() == 2


def test_reset_rebuilds_the_demo_tenant_and_keeps_its_identity(db_session):
    first = seed_demo(db_session, demo_config())
    second = seed_demo(db_session, demo_config(), reset=True)

    assert second.reset is True
    assert second.organization_id == first.organization_id
    assert second.trucks == 3
    assert second.devices == 3
    assert db_session.query(Organization).filter_by(name="Demo Corp").count() == 1
    assert db_session.query(User).filter(User.organization_id == first.organization_id).count() == 2


def test_reset_never_touches_another_organization(db_session, test_org, test_user):
    foreign_truck = Truck(id=900, plate="FOREIGN900", organization_id=test_org.id)
    db_session.add(foreign_truck)
    db_session.commit()

    seed_demo(db_session, demo_config())

    seed_demo(db_session, demo_config(), reset=True)

    assert db_session.get(Organization, test_org.id) is not None
    assert db_session.get(Truck, 900) is not None
    assert db_session.get(User, test_user.id) is not None


def test_seed_refuses_to_adopt_a_truck_owned_by_another_organization(
    db_session, test_org, test_truck
):
    # test_truck uses id 1, which the demo fleet also wants.
    with pytest.raises(SeedError):
        seed_demo(db_session, demo_config())

    db_session.refresh(test_truck)
    assert test_truck.organization_id == test_org.id


def test_seed_rejects_short_demo_password(db_session):
    with pytest.raises(SeedError):
        seed_demo(db_session, demo_config(admin_password="corta"))


def test_seed_leaves_the_demo_invitation_closed(db_session):
    """La demo se entra por el botón; un código abierto deja que cualquiera
    se registre en Demo Corp y esas cuentas sobreviven a los resets."""
    result = seed_demo(db_session, demo_config())

    organization = db_session.get(Organization, result.organization_id)

    assert organization.invitation_active is False


def test_renew_restarts_the_same_trip_of_the_truck_that_finished(db_session):
    """Se reusa el viaje: con un cron cada 15 min, clonar llenaría Rutas de filas."""
    seed_demo(db_session, demo_config())
    finished = db_session.query(Trip).filter(Trip.external_ref == "DEMO-003").one()
    assert finished.status == "done"
    trip_id = finished.id
    paradas = [(stop.seq, stop.lat, stop.lng) for stop in finished.stops]

    result = renew_demo_trips(db_session, demo_config())

    assert result.renewed == [(3, "DEMO-003")]
    assert result.skipped == 2
    assert db_session.query(Trip).count() == 3
    reiniciado = db_session.get(Trip, trip_id)
    assert reiniciado.status == "planned"
    assert [(s.seq, s.lat, s.lng) for s in reiniciado.stops] == paradas
    assert all(stop.status == "pending" for stop in reiniciado.stops)
    assert all(stop.arrived_at is None for stop in reiniciado.stops)


def test_renew_is_idempotent(db_session):
    seed_demo(db_session, demo_config())
    first = renew_demo_trips(db_session, demo_config())
    second = renew_demo_trips(db_session, demo_config())

    assert len(first.renewed) == 1
    assert second.renewed == []
    assert second.skipped == 3
    assert db_session.query(Trip).count() == 3


def test_renew_does_not_touch_a_truck_with_an_open_trip(db_session):
    seed_demo(db_session, demo_config())

    renew_demo_trips(db_session, demo_config())

    truck_1 = db_session.query(Trip).filter(Trip.truck_id == 1).all()
    assert [trip.external_ref for trip in truck_1] == ["DEMO-001"]
    assert truck_1[0].status == "in_progress"


def test_renew_requires_the_demo_tenant(db_session):
    with pytest.raises(SeedError):
        renew_demo_trips(db_session, demo_config())


def test_a_seeded_done_trip_has_its_stops_delivered(db_session):
    """"Finalizado" con tres destinos pendientes es una contradicción en la base."""
    seed_demo(db_session, demo_config())

    done = db_session.query(Trip).filter(Trip.external_ref == "DEMO-003").one()

    assert all(stop.status == "delivered" for stop in done.stops)
    assert all(stop.arrived_at is not None for stop in done.stops)
    assert all(stop.departed_at is not None for stop in done.stops)
