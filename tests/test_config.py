"""Configuración de entorno para despliegue: normalización de URL y fortaleza de la clave."""

import pytest
from pydantic import ValidationError

from source.database.config import Settings

VALID_SECRET = "0123456789abcdef0123456789abcdef"


def test_database_url_normalizes_render_style_scheme():
    settings = Settings(
        database_url="postgres://user:pass@host:5432/itertrack",
        secret_key=VALID_SECRET,
    )

    assert settings.database_url == "postgresql+psycopg2://user:pass@host:5432/itertrack"


def test_database_url_normalizes_plain_postgresql_scheme():
    settings = Settings(
        database_url="postgresql://user:pass@host:5432/itertrack",
        secret_key=VALID_SECRET,
    )

    assert settings.database_url == "postgresql+psycopg2://user:pass@host:5432/itertrack"


def test_database_url_keeps_explicit_driver_untouched():
    original = "postgresql+psycopg2://user:pass@host:5432/itertrack"

    settings = Settings(database_url=original, secret_key=VALID_SECRET)

    assert settings.database_url == original


def test_database_url_keeps_sqlite_untouched():
    settings = Settings(database_url="sqlite:///:memory:", secret_key=VALID_SECRET)

    assert settings.database_url == "sqlite:///:memory:"


def test_short_secret_key_is_rejected():
    with pytest.raises(ValidationError) as error:
        Settings(database_url="sqlite:///:memory:", secret_key="corta")

    assert "SECRET_KEY" in str(error.value)


def test_secret_key_with_padding_whitespace_is_stripped():
    settings = Settings(
        database_url="sqlite:///:memory:",
        secret_key=f"  {VALID_SECRET}  ",
    )

    assert settings.secret_key == VALID_SECRET
