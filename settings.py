"""Pydantic-validated application configuration."""
from typing import Any

from pydantic import AnyHttpUrl, BaseSettings, Field, root_validator


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


class Settings(BaseSettings):
    """Top level settings for the app."""

    # Debug mode should be enabled when running locally. This will show more error
    # tracebacks rather than hiding them.
    debug = False

    # Turning this on will print all SQL queries to the console. Very noisy.
    trace_queries = False

    # Databse connection settings.
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    # TEMPORARY: will be entirely replaced by Auth0 eventually.
    api_key: str

    # Transaction matching API settings.
    txm: TXMSettings = Field(default_factory=TXMSettings)

    # Number of jobs for workers to pull at once
    # The higher this is, the more work individual workers will do, but with
    # better per-worker performance.
    worker_concurrency: int = 50


settings = Settings()
