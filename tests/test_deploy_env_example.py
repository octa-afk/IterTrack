"""El `.env` de ejemplo es un contrato: si no arranca la demo, no sirve de ejemplo.

`scripts/seed_demo.py` rechaza contraseñas de menos de 12 caracteres, y el
entrypoint del contenedor corre el seed en el primer arranque. Un ejemplo con
una contraseña corta rompe el despliegue antes de que la app escuche.
"""

import re
from pathlib import Path

import pytest

ENV_EXAMPLE = Path(__file__).resolve().parent.parent / "deploy" / ".env.example"

MIN_PASSWORD_LENGTH = 12

PUBLIC_DEMO_PASSWORDS = (
    "DEMO_ADMIN_PASSWORD",
    "DEMO_MEMBER_PASSWORD",
    "ADMIN_API_PASSWORD",
)


def _read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


@pytest.mark.parametrize("name", PUBLIC_DEMO_PASSWORDS)
def test_demo_passwords_satisfy_the_seed_policy(name: str) -> None:
    value = _read_env().get(name)

    assert value is not None, f"falta {name} en deploy/.env.example"
    assert len(value) >= MIN_PASSWORD_LENGTH, (
        f"{name} tiene {len(value)} caracteres y el seed exige "
        f"{MIN_PASSWORD_LENGTH}: el primer arranque fallaría"
    )
    assert re.search(r"[A-Za-z]", value), f"{name} necesita al menos una letra"
    assert re.search(r"\d", value), f"{name} necesita al menos un número"


def test_demo_credentials_match_the_worker_credentials() -> None:
    env = _read_env()

    assert env["ADMIN_API_USER"] == env["DEMO_ADMIN_USERNAME"], (
        "el worker del simulador aprovisiona dispositivos con ADMIN_API_USER; "
        "si no coincide con el admin del seed no puede autenticarse"
    )
    assert env["ADMIN_API_PASSWORD"] == env["DEMO_ADMIN_PASSWORD"], (
        "el worker del simulador usa ADMIN_API_PASSWORD para loguearse"
    )


def test_the_published_demo_account_is_the_read_only_member() -> None:
    """`/config` publica la cuenta de solo lectura, nunca la de administración."""
    env = _read_env()

    assert env["DEMO_USERNAME"] == env["DEMO_MEMBER_USERNAME"], (
        "el visitante debe entrar como miembro; el admin de la demo no se publica"
    )
    assert env["DEMO_PASSWORD"] == env["DEMO_MEMBER_PASSWORD"]
