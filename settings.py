"""Pydantic-validated application configuration."""
from pydantic import BaseSettings


class DatabaseSettings(BaseSettings):
    """
    Settings for the PostgreSQL database connection.
    The DSN value must have a placeholder ({}) for the database name.
    """

    dsn = "postgresql://postgres:postgres@localhost:5432/{}"
    dbname = "bullsquid"

    class Config:
        """Set PostgreSQL settings with postgres_host, postgres_port, et cetera."""

        env_prefix = "database_"


class Settings(BaseSettings):
    """Top level settings for the app."""

    debug = False
    trace_queries = False
    database = DatabaseSettings()

    # TEMPORARY: will be entirely replaced by Auth0 eventually.
    api_key: str


settings = Settings()
