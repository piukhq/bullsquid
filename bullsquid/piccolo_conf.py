"""Piccolo ORM configuration."""
from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine

from settings import settings

DB = PostgresEngine(
    config={
        "database": settings.postgres.dbname,
        "user": settings.postgres.user,
        "password": settings.postgres.password,
        "host": settings.postgres.host,
        "port": settings.postgres.port,
    },
    log_queries=settings.debug,
)

APP_REGISTRY = AppRegistry(apps=["bullsquid.mids.piccolo_app"])
