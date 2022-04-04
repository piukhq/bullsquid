"""
Defines the create_app function used to initialize the application.
"""
from asyncpg.exceptions import PostgresError
from fastapi import Depends, FastAPI, Request
from loguru import logger
from piccolo.engine import engine_finder
from starlette.responses import JSONResponse
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from bullsquid.api.auth import check_api_key
from bullsquid.api.errors import error_response
from bullsquid.merchant_data.api.routers import v1 as merchant_data_v1
from bullsquid.status.views import router as status_api


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""

    app = FastAPI(
        title="Portal API",
        description="API for interacting with the portal backend.",
        version="1.0.0",
    )
    app.include_router(status_api, tags=["Status"])
    app.include_router(
        merchant_data_v1,
        prefix="/merchant_data",
        tags=["Merchant Data Management"],
        dependencies=[Depends(check_api_key)],
    )

    @app.exception_handler(Exception)
    async def generic_error_handler(_request: Request, ex: Exception) -> JSONResponse:
        """Handles generic exceptions."""
        return error_response(ex)

    @app.exception_handler(OSError)
    async def os_error_handler(_request: Request, ex: OSError) -> JSONResponse:
        """Handles OSErrors, usually caused by connection failure to other services."""
        return error_response(
            ex,
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            message="Unable to process request due to connection failure to another service.",
        )

    @app.exception_handler(PostgresError)
    async def postgres_error_handler(
        _request: Request, ex: PostgresError
    ) -> JSONResponse:
        """Handles PostgresErrors, usually caused by bad queries or validation gaps."""
        return error_response(
            ex,
            message="Unable to process request due to a database error.",
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
