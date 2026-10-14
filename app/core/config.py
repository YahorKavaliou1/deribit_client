from pydantic import AmqpDsn, BaseModel, ConfigDict, Field, HttpUrl, PositiveFloat, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

_ENV_FILE = ".env"


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection settings.

    Reuses the ``POSTGRES_*`` variables of the official postgres image, so a single
    ``.env`` file configures both the database container and the application.
    """

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", env_file=_ENV_FILE, extra="ignore")

    user: str
    password: SecretStr
    db: str
    host: str = "localhost"
    port: int = Field(default=5432, gt=0, lt=65536)

    @property
    def url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.db,
        )


class CelerySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CELERY_", env_file=_ENV_FILE, extra="ignore")

    broker_url: AmqpDsn
    price_fetch_interval_seconds: PositiveFloat = 60.0


class DeribitSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DERIBIT_", env_file=_ENV_FILE, extra="ignore")

    base_url: HttpUrl = HttpUrl("https://www.deribit.com/api/v2")
    request_timeout_seconds: PositiveFloat = 10.0


class Settings(BaseModel):
    """Root application settings.

    Created once by an application factory and passed down explicitly;
    there is intentionally no module-level settings instance.
    """

    model_config = ConfigDict(frozen=True)

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    deribit: DeribitSettings = Field(default_factory=DeribitSettings)
