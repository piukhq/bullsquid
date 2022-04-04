"""Pydantic-validated application configuration."""
from pydantic import BaseSettings


class PostgresSettings(BaseSettings):
    """Settings for the PostgreSQL database connection."""

    host = "localhost"
    port = 5432
    user = "postgres"
    password = ""
    dbname = "bullsquid"

    class Config:
        """Set PostgreSQL settings with postgres_host, postgres_port, et cetera."""

        env_prefix = "postgres_"


class Settings(BaseSettings):
    """Top level settings for the app."""

    debug = False
    trace_queries = False
    postgres = PostgresSettings()

    # TEMPORARY: will be entirely replaced by Auth0 eventually.
    api_key: str


settings = Settings()
