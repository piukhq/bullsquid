# pylint: disable=too-few-public-methods
"""Pydantic-validated application configuration."""
from pydantic import BaseSettings


class PostgresSettings(BaseSettings):
    """Settings for the PostgreSQL database connection."""

    host = "localhost"
    port = 5432
    user = "bullsquid"
    password = ""
    dbname = "bullsquid"

    class Config:
        """Set PostgreSQL settings with postgres_host, postgres_port, et cetera."""

        env_prefix = "postgres_"


class Settings(BaseSettings):
    """Top level settings for the app."""

    debug = False
    postgres = PostgresSettings()


settings = Settings()
