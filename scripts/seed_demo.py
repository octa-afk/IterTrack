"""Demo tenant seed: the customer-facing demo, safe to reset at any time.

Separate from `bootstrap_platform.py` on purpose. The platform owner is created
once and must never be touched by a demo reset; this script only owns the
`Demo Corp` tenant and everything inside it.

Usage:
    env/bin/python -m scripts.seed_demo            # create what is missing
    env/bin/python -m scripts.seed_demo --reset    # wipe the demo tenant first

Required environment variables (see .env.example):
    DEMO_ADMIN_PASSWORD, DEMO_MEMBER_PASSWORD
"""

import argparse
import json
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from scripts.simulate_trucks import build_truck_configs, truck_plates
from source.database.database import SessionLocal
from source.models.destination import (
    AddressCache,
    Charger,
    Depot,
    Trip,
    TripStop,
)
from source.models.device import Device, DeviceAssignment
from source.models.ingestion import IngestedPoint, RejectedIngestPoint
from source.models.organization import Organization
from source.models.truck import TrackingPoint, Truck
from source.models.user import ROLE_MEMBER, ROLE_ORG_ADMIN, User
from source.services.auth import hash_password

MIN_PASSWORD_LENGTH = 12
DEFAULT_ORG_NAME = "Demo Corp"
DEFAULT_TRUCK_COUNT = 3
DEFAULT_BASE_ID = 1
DEFAULT_BASE_PLATE = "ABC123"
DEFAULT_DEVICE_PREFIX = "SIM"
# Datos mínimos para que la sección Rutas sea usable en la demo.
DEMO_CHARGERS = ("Colchones Sur", "Ferretería Norte", "Bebidas del Sur")
DEFAULT_DEPOT = "Depósito Centro"
# Plaza San Martín, centro de Córdoba.
DEFAULT_DEPOT_LAT = -31.4135
DEFAULT_DEPOT_LNG = -64.1811
# Un viaje por camión, con las paradas tomadas del circuito que recorre el
# simulador y ya resueltas: no dependen del geocoder. Cada camión recorre el
# mismo circuito con una fase distinta, así que sus paradas salen del tercio que
# le toca (ver `_demo_trip_indexes`). Sin esto la sección Rutas queda vacía y el
# mapa no tiene destinos que mostrar.
#
# El último viaje se siembra cerrado a propósito: con los tres abiertos ningún
# camión figura disponible y el formulario no tendría a quién asignarle uno nuevo.
DEMO_TRIP_STATUSES = ("in_progress", "in_progress", "done")
ROUTE_FILE = Path(__file__).resolve().parent / "cordoba_route.json"


class SeedError(ValueError):
    """Configuration or state problem that prevents seeding."""


@dataclass(frozen=True)
class DemoSeedConfig:
    org_name: str
    admin_username: str
    admin_email: str
    admin_full_name: str
    admin_password: str
    member_username: str
    member_email: str
    member_full_name: str
    member_password: str
    truck_count: int
    base_id: int
    base_plate: str
    device_prefix: str


@dataclass(frozen=True)
class DemoSeedResult:
    organization_id: int
    trucks: int
    devices: int
    reset: bool
    invitation_code: str
    chargers: int
    depots: int
    trips: int
    trips_rebuilt: int


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SeedError(f"Falta la variable de entorno {name}.")
    return value


def _password(name: str) -> str:
    value = _required(name)
    if len(value) < MIN_PASSWORD_LENGTH:
        raise SeedError(f"{name} debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    return value


def _demo_trip_indexes(
    route_length: int, route_offset: int, truck_count: int
) -> list[int]:
    """Tres paradas dentro del tercio del circuito que le toca a ese camión.

    Los camiones comparten el mismo circuito repartidos en fases. Si las paradas
    se eligieran del circuito entero, los tres viajes tendrían destinos
    mezclados y un camión pasaría por una parada "suya" media vuelta después.
    """
    if route_length < 1:
        raise SeedError("La ruta de demo está vacía.")
    tramo = route_length / truck_count
    return [
        int(route_offset + tramo * fraccion) % route_length
        for fraccion in (0.25, 0.5, 0.75)
    ]


def config_from_env() -> DemoSeedConfig:
    truck_count = int(os.getenv("DEMO_TRUCK_COUNT", str(DEFAULT_TRUCK_COUNT)))
    if truck_count < 1:
        raise SeedError("DEMO_TRUCK_COUNT debe ser al menos 1.")
    return DemoSeedConfig(
        org_name=os.getenv("DEMO_ORG_NAME", DEFAULT_ORG_NAME).strip() or DEFAULT_ORG_NAME,
        admin_username=os.getenv("DEMO_ADMIN_USERNAME", "demo-admin").strip() or "demo-admin",
        admin_email=os.getenv("DEMO_ADMIN_EMAIL", "demo-admin@itertrack.local").strip()
        or "demo-admin@itertrack.local",
        admin_full_name=os.getenv("DEMO_ADMIN_FULL_NAME", "Demo Admin").strip() or "Demo Admin",
        admin_password=_password("DEMO_ADMIN_PASSWORD"),
        member_username=os.getenv("DEMO_MEMBER_USERNAME", "demo").strip() or "demo",
        member_email=os.getenv("DEMO_MEMBER_EMAIL", "demo@itertrack.local").strip()
        or "demo@itertrack.local",
        member_full_name=os.getenv("DEMO_MEMBER_FULL_NAME", "Demo User").strip() or "Demo User",
        member_password=_password("DEMO_MEMBER_PASSWORD"),
        truck_count=truck_count,
        base_id=int(os.getenv("DEMO_TRUCK_BASE_ID", str(DEFAULT_BASE_ID))),
        base_plate=os.getenv("DEMO_TRUCK_BASE_PLATE", DEFAULT_BASE_PLATE).strip()
        or DEFAULT_BASE_PLATE,
        device_prefix=os.getenv("DEMO_DEVICE_PREFIX", DEFAULT_DEVICE_PREFIX).strip()
        or DEFAULT_DEVICE_PREFIX,
    )


def _reset_tenant(db: Session, organization_id: int) -> None:
    """Delete the tenant payload in foreign-key order, scoped to the demo org."""
    device_ids = [
        device.id
        for device in db.query(Device).filter(Device.organization_id == organization_id)
    ]
    truck_ids = [
        truck.id for truck in db.query(Truck).filter(Truck.organization_id == organization_id)
    ]

    if device_ids:
        db.query(RejectedIngestPoint).filter(
            RejectedIngestPoint.device_id.in_(device_ids)
        ).delete(synchronize_session=False)
        db.query(IngestedPoint).filter(IngestedPoint.device_id.in_(device_ids)).delete(
            synchronize_session=False
        )
        db.query(DeviceAssignment).filter(
            DeviceAssignment.device_id.in_(device_ids)
        ).delete(synchronize_session=False)
        db.query(Device).filter(Device.id.in_(device_ids)).delete(synchronize_session=False)

    # Los viajes y sus paradas primero: `trips` referencia camiones, dadores y
    # depósitos. Sin esto el reset choca contra las claves foráneas en Postgres.
    trip_ids = [
        trip.id
        for trip in db.query(Trip).filter(Trip.organization_id == organization_id)
    ]
    if trip_ids:
        db.query(TripStop).filter(TripStop.trip_id.in_(trip_ids)).delete(
            synchronize_session=False
        )
        db.query(Trip).filter(Trip.id.in_(trip_ids)).delete(synchronize_session=False)
    db.query(Charger).filter(Charger.organization_id == organization_id).delete(
        synchronize_session=False
    )
    db.query(Depot).filter(Depot.organization_id == organization_id).delete(
        synchronize_session=False
    )
    db.query(AddressCache).filter(
        AddressCache.organization_id == organization_id
    ).delete(synchronize_session=False)

    if truck_ids:
        db.query(DeviceAssignment).filter(
            DeviceAssignment.truck_id.in_(truck_ids)
        ).delete(synchronize_session=False)
        db.query(IngestedPoint).filter(IngestedPoint.truck_id.in_(truck_ids)).delete(
            synchronize_session=False
        )
        db.query(TrackingPoint).filter(TrackingPoint.truck_id.in_(truck_ids)).delete(
            synchronize_session=False
        )
        db.query(Truck).filter(Truck.id.in_(truck_ids)).delete(synchronize_session=False)

    db.query(User).filter(User.organization_id == organization_id).delete(
        synchronize_session=False
    )
    db.commit()


def seed_demo(db: Session, config: DemoSeedConfig, reset: bool = False) -> DemoSeedResult:
    """Create (or reset) the demo tenant. Never touches any other organization."""
    if len(config.admin_password) < MIN_PASSWORD_LENGTH:
        raise SeedError(
            f"La contraseña del admin demo debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
        )
    if len(config.member_password) < MIN_PASSWORD_LENGTH:
        raise SeedError(
            f"La contraseña del miembro demo debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
        )

    organization = db.query(Organization).filter(Organization.name == config.org_name).first()
    if organization is None:
        organization = Organization(
            name=config.org_name,
            invitation_code=secrets.token_urlsafe(12),
            invitation_expires_at=None,
            # La demo no se une por registro: el visitante entra con el boton
            # del login. Un codigo activo dejaria que cualquiera se registre en
            # Demo Corp, y esas cuentas sobreviven a los resets.
            invitation_revoked_at=datetime.now(UTC),
        )
        db.add(organization)
        db.flush()
    elif reset:
        _reset_tenant(db, organization.id)

    admin = (
        db.query(User)
        .filter(User.username == config.admin_username)
        .first()
    )
    if admin is None:
        db.add(
            User(
                username=config.admin_username,
                email=config.admin_email,
                full_name=config.admin_full_name,
                hashed_password=hash_password(config.admin_password),
                organization_id=organization.id,
                role=ROLE_ORG_ADMIN,
            )
        )
    else:
        admin.role = ROLE_ORG_ADMIN
        admin.organization_id = organization.id
        admin.hashed_password = hash_password(config.admin_password)

    member = db.query(User).filter(User.username == config.member_username).first()
    if member is None:
        db.add(
            User(
                username=config.member_username,
                email=config.member_email,
                full_name=config.member_full_name,
                hashed_password=hash_password(config.member_password),
                organization_id=organization.id,
                role=ROLE_MEMBER,
            )
        )
    else:
        member.role = ROLE_MEMBER
        member.organization_id = organization.id
        member.hashed_password = hash_password(config.member_password)

    db.flush()

    # El seed no inyecta posiciones: la primera ubicación la reporta el
    # dispositivo (POST /devices/ingest), igual que el hardware real.
    # La ruta se lee acá porque fija la fase de cada camión: sin `route_length`
    # `build_truck_configs` reparte offsets 0, 1, 2 y los tres viajes terminarían
    # con las mismas paradas.
    ruta = json.loads(ROUTE_FILE.read_text(encoding="utf-8"))
    truck_configs = build_truck_configs(
        base_id=config.base_id,
        base_plate=config.base_plate,
        count=config.truck_count,
        route_length=len(ruta),
        plates=truck_plates(),
    )

    trucks_created = 0
    devices_created = 0
    for truck_config in truck_configs:
        truck = db.get(Truck, truck_config.truck_id)
        if truck is not None and truck.organization_id != organization.id:
            raise SeedError(
                f"El camión #{truck_config.truck_id} ya pertenece a otra organización. "
                "El seed de demo nunca adopta datos ajenos."
            )
        if truck is None:
            truck = Truck(
                id=truck_config.truck_id,
                plate=truck_config.plate,
                organization_id=organization.id,
            )
            db.add(truck)
            db.flush()
            trucks_created += 1
        else:
            truck.organization_id = organization.id
            # La patente converge con la flota configurada: sin esto, cambiar
            # `TRUCK_PLATES` no renombra nada hasta un `--reset`.
            truck.plate = truck_config.plate

        # Same formula the simulator uses, so device mode recognises these
        # as its own instead of a real ESP32.
        identifier = f"{config.device_prefix}-{truck.id:03d}"
        device = db.query(Device).filter(Device.identifier == identifier).first()
        if device is not None and device.organization_id != organization.id:
            raise SeedError(
                f"El dispositivo '{identifier}' ya pertenece a otra organización. "
                "El seed de demo nunca adopta datos ajenos."
            )
        if device is None:
            device = Device(
                identifier=identifier,
                token_hash=secrets.token_hex(32),
                organization_id=organization.id,
            )
            db.add(device)
            db.flush()
            db.add(DeviceAssignment(device_id=device.id, truck_id=truck.id, valid_from=datetime.now(UTC)))
            devices_created += 1
        else:
            device.organization_id = organization.id

    # Un viaje siempre pertenece a un dador de carga y sale de un depósito. Sin
    # esto la sección Rutas queda vacía y sin forma de crear el primero.
    chargers: list[Charger] = []
    chargers_created = 0
    for nombre in DEMO_CHARGERS:
        charger = (
            db.query(Charger)
            .filter(Charger.organization_id == organization.id, Charger.name == nombre)
            .first()
        )
        if charger is None:
            charger = Charger(organization_id=organization.id, name=nombre)
            db.add(charger)
            db.flush()
            chargers_created += 1
        chargers.append(charger)

    depot = (
        db.query(Depot)
        .filter(Depot.organization_id == organization.id, Depot.name == DEFAULT_DEPOT)
        .first()
    )
    depot_created = False
    if depot is None:
        depot = Depot(
            organization_id=organization.id,
            name=DEFAULT_DEPOT,
            lat=DEFAULT_DEPOT_LAT,
            lng=DEFAULT_DEPOT_LNG,
        )
        db.add(depot)
        db.flush()
        depot_created = True

    # Un viaje por camión. El seed es dueño de los viajes de demo (los identifica
    # por `external_ref`), así que cuando la ruta o el reparto de fases cambian
    # reescribe sus paradas en lugar de dejar datos de una corrida anterior.
    trips_created = 0
    trips_rebuilt = 0
    for indice, truck_config in enumerate(truck_configs):
        referencia = f"DEMO-{indice + 1:03d}"
        puntos = [
            (ruta[posicion][0], ruta[posicion][1])
            for posicion in _demo_trip_indexes(
                len(ruta), truck_config.route_offset, len(truck_configs)
            )
        ]
        viaje = (
            db.query(Trip)
            .filter(
                Trip.organization_id == organization.id,
                Trip.external_ref == referencia,
            )
            .first()
        )
        if viaje is None:
            viaje = Trip(
                organization_id=organization.id,
                charger_id=chargers[indice % len(chargers)].id,
                truck_id=truck_config.truck_id,
                departure_at=datetime.now(UTC),
                status=DEMO_TRIP_STATUSES[indice % len(DEMO_TRIP_STATUSES)],
                external_ref=referencia,
                depot_id=depot.id,
            )
            db.add(viaje)
            db.flush()
            trips_created += 1
            reescribir = True
        else:
            # La dirección incluye la patente, así que un renombre también cuenta
            # como cambio: sin esto la parada diría la patente vieja.
            actuales = [
                (parada.address, parada.lat, parada.lng) for parada in viaje.stops
            ]
            reescribir = actuales != [
                (f"Parada {seq} · {truck_config.plate}", lat, lng)
                for seq, (lat, lng) in enumerate(puntos, start=1)
            ]

        if not reescribir:
            continue
        viaje.stops.clear()
        db.flush()
        for seq, (lat, lng) in enumerate(puntos, start=1):
            viaje.stops.append(
                TripStop(
                    seq=seq,
                    address=f"Parada {seq} · {truck_config.plate}",
                    lat=lat,
                    lng=lng,
                    geo_source="provided",
                    needs_review=False,
                )
            )
        trips_rebuilt += 1

    db.commit()
    db.refresh(organization)
    return DemoSeedResult(
        organization_id=organization.id,
        trucks=trucks_created,
        devices=devices_created,
        reset=reset,
        invitation_code=organization.invitation_code,
        chargers=chargers_created,
        depots=1 if depot_created else 0,
        trips=trips_created,
        trips_rebuilt=trips_rebuilt,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crea o resetea el tenant de demo (nunca toca otras organizaciones)."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Borra los datos del tenant de demo antes de volver a sembrarlo.",
    )
    args = parser.parse_args()

    try:
        config = config_from_env()
    except SeedError as error:
        print(f"⛔ {error}")
        return 1

    with SessionLocal() as db:
        result = seed_demo(db, config, reset=args.reset)

    modo = "reset" if result.reset else "sin reset"
    print(f"🏢 Demo '{config.org_name}' (id {result.organization_id}) — {modo}")
    print(f"🚚 Camiones creados: {result.trucks} | 📡 Dispositivos: {result.devices}")
    if result.trips or result.trips_rebuilt:
        print(
            f"🧭 Viajes demo: {result.trips} creados | "
            f"{result.trips_rebuilt} con paradas rehechas"
        )
    if result.chargers or result.depots:
        print(
            f"📦 Dadores de carga: {result.chargers} creados | "
            f"🏭 Depósito: {'creado' if result.depots else 'existía'}"
        )
    print("🔒 Invitación cerrada: la demo se entra con el botón del login.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
