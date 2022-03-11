"""Piccolo ORM configuration."""
from piccolo.engine.postgres import PostgresEngine

from piccolo_conf import APP_REGISTRY  # pylint: disable=unused-import
from settings import settings

DB = PostgresEngine(
    config={
        "database": f"{settings.postgres.dbname}_test",
        "user": settings.postgres.user,
        "password": settings.postgres.password,
        "host": settings.postgres.host,
        "port": settings.postgres.port,
    },
    log_queries=settings.debug,
)
