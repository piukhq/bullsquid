"""Pydantic-validated application configuration."""
from pathlib import Path
from typing import Any
from datetime import timedelta

import tomli
from pydantic import AnyHttpUrl, BaseSettings, Field, root_validator, validator
from pydantic.env_settings import SettingsSourceCallable
from url_normalize import url_normalize


def toml_settings_source(_: BaseSettings) -> dict[str, Any]:
    """
    Load settings from a ``config.toml`` file in the current working directory
    if it exists.
    """
    config_path = Path("config.toml")

    if not config_path.exists() or not config_path.is_file():
        return {}

    with config_path.open("rb") as config_file:
        return tomli.load(config_file)


class DatabaseSettings(BaseSettings):
    """
    Settings for the PostgreSQL database connection.
    The DSN value must have a placeholder ({}) for the database name.
    """

    class Config:
        """
        If using env variables, set database settings with database_dsn and
        database_dbname.
        """

        env_prefix = "database_"

    dsn = "postgresql://postgres:postgres@localhost:5432/{}?application_name=bullsquid"
    dbname = "bullsquid"


class TXMSettings(BaseSettings):
    """Settings for the transaction matching API."""

    class Config:
        """
        If using env variables, set TXM settings with txm_base_url and
        txm_api_key.
        """

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
        """
        If using env variables, set OAuth settings with oauth_domain,
        oauth_audience, et cetera.
        """

        env_prefix = "oauth_"

    domain: AnyHttpUrl | None
    audience: str = "https://portal.bink.com"
    algorithms: list[str] = ["RS256"]
    leeway: int = 10
    mgmt_client_id: str = ""
    mgmt_client_secret: str = ""

    @validator("domain")
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        """Normalizing the domain URL gives us a better chance of not mistyping it."""
        return url_normalize(v)


class SentrySettings(BaseSettings):
    """
    Settings for the Sentry SDK. If DSN is None, Sentry SDK will not be
    initialised and the other settings will be ignored.
    """

    class Config:
        """
        If using env variables, set Sentry settings with sentry_dsn and
        sentry_env.
        """

        env_prefix = "sentry_"

    dsn: AnyHttpUrl | None
    env: str | None


class BlobStorageSettings(BaseSettings):
    """
    Settings for the Azure Blob Storage service. If DSN is None, the service
    will not be initialised and the other settings will be ignored.
    """

    class Config:
        """
        If using env variables, set Blob Storage settings with blob_storage_dsn
        and blob_storage_archive_container.
        """

        env_prefix = "blob_storage"

    dsn: str | None = None
    archive_container: str = "portal-archive"


class Settings(BaseSettings):
    """Top level settings for the app."""

    class Config:
        """Base settings configuration."""

        secrets_dir = "/mnt/secrets"

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> tuple[SettingsSourceCallable, ...]:
            """Include a TOML settings source."""
            return (
                init_settings,
                toml_settings_source,
                env_settings,
                file_secret_settings,
            )

    # Debug mode should be enabled when running locally. This will show more error
    # tracebacks rather than hiding them.
    debug = False

    # Turning this on will print all SQL queries to the console. Very noisy.
    trace_queries = False

    # Database connection settings.
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    # Transaction matching API settings.
    txm: TXMSettings = Field(default_factory=TXMSettings)

    # OAuth settings.
    oauth: OAuthSettings = Field(default_factory=OAuthSettings)

    # Sentry SDK settings.
    sentry: SentrySettings = Field(default_factory=SentrySettings)

    # Azure Blob Storage settings.
    blob_storage: BlobStorageSettings = Field(default_factory=BlobStorageSettings)

    # TEMPORARY: for compatibility until the frontend has transitioned over to
    # using OAuth.
    api_key: str | None = None

    # Number of jobs for workers to pull at once
    # The higher this is, the more work individual workers will do, but with
    # better per-worker performance.
    worker_concurrency: int = 50

    # Number of results for each page
    default_page_size = 20

    # How long we keep our user profiles before checking for updates
    user_profile_ttl = timedelta(weeks=2)


settings = Settings()
