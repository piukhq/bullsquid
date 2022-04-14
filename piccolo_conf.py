"""Piccolo ORM configuration."""
from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine

from settings import settings

DB = PostgresEngine(
    config={
        "dsn": settings.database.dsn.format(settings.database.dbname),
    },
    log_queries=settings.trace_queries,
)

APP_REGISTRY = AppRegistry(apps=["bullsquid.merchant_data.piccolo_app"])
