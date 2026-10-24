"""Configuración pública que el cliente lee antes de autenticarse.

La demo necesita que un visitante entre sin leer el README. El flag vive en el
servidor para que la misma imagen sirva a un cliente real con la demo apagada.
La cuenta publicada es de solo lectura: las credenciales de administración de
la demo nunca salen del servidor.
"""

from types import SimpleNamespace


def test_config_hides_the_demo_credentials_when_the_flag_is_off(client, monkeypatch):
    monkeypatch.setattr("source.main.settings", SimpleNamespace(demo_enabled=False))

    response = client.get("/config")

    assert response.status_code == 200
    assert response.json() == {"demo": {"enabled": False}}


def test_config_returns_the_public_read_only_demo_account(client, monkeypatch):
    monkeypatch.setattr(
        "source.main.settings",
        SimpleNamespace(
            demo_enabled=True,
            demo_username="demo",
            demo_password="demo-member-2026",
        ),
    )

    response = client.get("/config")

    assert response.status_code == 200
    assert response.json() == {
        "demo": {
            "enabled": True,
            "username": "demo",
            "password": "demo-member-2026",
        }
    }


def test_config_never_exposes_the_demo_admin_credentials(client, monkeypatch):
    """El admin de la demo existe para el seed y la operación, no para el visitante."""
    monkeypatch.setattr(
        "source.main.settings",
        SimpleNamespace(
            demo_enabled=True,
            demo_username="demo",
            demo_password="demo-member-2026",
            demo_admin_username="demo-admin",
            demo_admin_password="demo-admin-2026",
        ),
    )

    body = client.get("/config").text

    assert "demo-admin" not in body
    assert "demo-admin-2026" not in body
