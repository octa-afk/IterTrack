from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# A short key lets anyone forge an HS256 token and impersonate an admin, so the
# application refuses to start with one instead of failing silently in production.
MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Un visitante de la demo entra con un click sin leer el README. El flag
    # vive acá y no en el frontend para que la misma imagen sirva a un cliente
    # real con la demo apagada.
    #
    # `demo_username`/`demo_password` son la cuenta que se publica en /config:
    # una de solo lectura (`member`). Las credenciales de `demo_admin_*` son
    # para el seed y la operación y NUNCA salen del servidor: con el admin
    # público, cualquiera podía borrar el historial o desactivar camiones.
    demo_mode: bool = False
    demo_username: str = ""
    demo_password: str = ""
    demo_admin_username: str = ""
    demo_admin_password: str = ""

    # Geocoding de direcciones (destinos). `none` deja todo destino pendiente de
    # revisión manual, que es el comportamiento seguro por defecto: sin proveedor
    # configurado no se llama a ningún servicio externo.
    # Valores: none | nominatim.
    geocoder_provider: str = "none"
    geocoder_url: str = "https://nominatim.openstreetmap.org"
    geocoder_user_agent: str = "IterTrack/1.0 (fleet telemetry; contacto@itertrack.local)"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        """Accept the scheme managed platforms hand out instead of a driver URL.

        Render, Railway and Heroku expose `postgres://` or `postgresql://`, which
        SQLAlchemy rejects because it cannot pick a driver from them.
        """
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg2://" + value[len(prefix) :]
        return value

    @property
    def demo_enabled(self) -> bool:
        """Solo hay demo si el flag está encendido y hay cuenta pública que dar."""
        return (
            self.demo_mode
            and bool(self.demo_username)
            and bool(self.demo_password)
        )

    @field_validator("secret_key")
    @classmethod
    def _validate_secret_key(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} characters. "
                "A short key lets anyone forge an admin JWT."
            )
        return stripped


settings = Settings()
