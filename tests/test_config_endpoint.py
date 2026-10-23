"""Configuración pública que el cliente lee antes de autenticarse.

La demo necesita que un visitante entre sin leer el README. El flag vive en el
servidor para que la misma imagen sirva a un cliente real con la demo apagada.
"""

from types import SimpleNamespace


def test_config_hides_the_demo_credentials_when_the_flag_is_off(client, monkeypatch):
    monkeypatch.setattr("source.main.settings", SimpleNamespace(demo_enabled=False))

    response = client.get("/config")

    assert response.status_code == 200
    assert response.json() == {"demo": {"enabled": False}}


def test_config_returns_the_public_demo_credentials_when_the_flag_is_on(
    client, monkeypatch
):
    monkeypatch.setattr(
        "source.main.settings",
        SimpleNamespace(
            demo_enabled=True,
            demo_admin_username="demo-admin",
            demo_admin_password="demo-admin-2026",
        ),
    )

    response = client.get("/config")

    assert response.status_code == 200
    assert response.json() == {
        "demo": {
            "enabled": True,
            "username": "demo-admin",
            "password": "demo-admin-2026",
        }
    }
