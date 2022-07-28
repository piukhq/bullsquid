"""Pydantic-validated application configuration."""
from typing import Any

from pydantic import AnyHttpUrl, BaseSettings, Field, root_validator, validator
from url_normalize import url_normalize


class DatabaseSettings(BaseSettings):
    """
    Settings for the PostgreSQL database connection.
    The DSN value must have a placeholder ({}) for the database name.
    """

    class Config:
        """Set database settings with database_dsn and database_dbname."""

        env_prefix = "database_"

    dsn = "postgresql://postgres:postgres@localhost:5432/{}"
    dbname = "bullsquid"


class TXMSettings(BaseSettings):
    """Settings for the transaction matching API."""

    class Config:
        """Set TXM settings with txm_base_url and txm_api_key."""

        env_prefix = "txm_"

    base_url: AnyHttpUrl | None
    api_key: str | None

    @root_validator
    @classmethod
    def validate_all_are_present(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Either all or none of these settings must be present."""
        if not all(values.values()) and any(values.values()):
            raise ValueError(
                "If one TXM setting is provided, all others must also be provided."
            )

        return values


class OAuthSettings(BaseSettings):
    """Settings for the OAuth provider."""

    class Config:
        """Set OAuth settings with oauth_domain, oauth_audience, et cetera."""

        env_prefix = "oauth_"

    domain: AnyHttpUrl | None
    audience: str = "https://portal.bink.com"
    algorithms: list[str] = ["RS256"]
    leeway: int = 10

    @validator("domain")
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        """Normalizing the domain URL gives us a better chance of not mistyping it."""
        return url_normalize(v)


class Settings(BaseSettings):
    """Top level settings for the app."""

    # Debug mode should be enabled when running locally. This will show more error
    # tracebacks rather than hiding them.
    debug = False

    # Turning this on will print all SQL queries to the console. Very noisy.
    trace_queries = False

    # Databse connection settings.
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    # Transaction matching API settings.
    txm: TXMSettings = Field(default_factory=TXMSettings)

    # OAuth settings.
    oauth: OAuthSettings = Field(default_factory=OAuthSettings)

    # TEMPORARY: for compatibility until the frontend has transitioned over to
    # using OAuth.
    api_key: str | None = None

    # Number of jobs for workers to pull at once
    # The higher this is, the more work individual workers will do, but with
    # better per-worker performance.
    worker_concurrency: int = 50


settings = Settings()
