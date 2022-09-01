"""Piccolo ORM configuration."""
from piccolo.engine.postgres import PostgresEngine

from bullsquid.piccolo_conf import APP_REGISTRY  # pylint: disable=unused-import
from bullsquid.settings import settings

DB = PostgresEngine(
    config={
        "dsn": settings.database.dsn.format(f"{settings.database.dbname}_test"),
    },
    log_queries=settings.debug,
)
