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
    # real con la demo apagada; las credenciales son públicas por diseño.
    demo_mode: bool = False
    demo_admin_username: str = ""
    demo_admin_password: str = ""
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
        """Solo hay demo si el flag está encendido y hay credenciales que dar."""
        return (
            self.demo_mode
            and bool(self.demo_admin_username)
            and bool(self.demo_admin_password)
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
