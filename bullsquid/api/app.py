"""
Defines the create_app function used to initialize the application.
"""
import sentry_sdk
from asyncpg.exceptions import PostgresError
from fastapi import FastAPI, Request
from loguru import logger
from piccolo.engine import engine_finder
from starlette.responses import JSONResponse
from starlette.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from bullsquid.mids.api.routers import v1 as mids_v1
from settings import settings


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""

    app = FastAPI(
        title="Portal API",
        description="API for interacting with the portal backend.",
        version="1.0.0",
    )
    app.include_router(mids_v1, prefix="/mid_management", tags=["MID Management"])

    @app.exception_handler(OSError)
    async def os_error_handler(_request: Request, exc: OSError) -> JSONResponse:
        """Handles OSErrors, usually caused by connection failure to other services."""
        if settings.debug:
            logger.exception(exc)

        sentry_sdk.capture_exception(exc)

        return JSONResponse(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": {
                    "msg": "Unable to process request due to an internal error.",
                }
            },
        )

    @app.exception_handler(PostgresError)
    async def postgres_error_handler(
        _request: Request, exc: PostgresError
    ) -> JSONResponse:
        """Handles PostgresErrors, usually caused by bad queries or validation gaps."""
        if settings.debug:
            logger.exception(exc)

        sentry_sdk.capture_exception(exc)

        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": {
                    "msg": "Unable to process request due to a database error.",
                }
            },
        )

    @app.on_event("startup")
    async def open_database_connection_pool() -> None:
        """Opens the database connection pool on application startup."""
        try:
            engine = engine_finder()
            if not engine:
                raise RuntimeError("No database engine found")
            await engine.start_connection_pool()
        except Exception as ex:  # pylint: disable=broad-except
            logger.error(f"Unable to connect to the database: {ex}")

    @app.on_event("shutdown")
    async def close_database_connection_pool() -> None:
        """Closes the database connection pool on application shutdown."""
        try:
            engine = engine_finder()
            if not engine:
                raise RuntimeError("No database engine found")
            await engine.close_connection_pool()
        except Exception as ex:  # pylint: disable=broad-except
            logger.error(f"Unable to connect to the database: {ex}")

    return app
