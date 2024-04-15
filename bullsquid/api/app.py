"""
Defines the create_app function used to initialize the application.
"""

from asyncpg.exceptions import PostgresError
from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from piccolo.engine import engine_finder
from starlette.responses import JSONResponse

from bullsquid.api.auth import jwt_bearer
from bullsquid.api.errors import error_response
from bullsquid.customer_wallet.router import router as customer_wallet_router
from bullsquid.merchant_data.router import router as merchant_data_router
from bullsquid.status.views import router as status_api


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""

    app = FastAPI(
        title="Portal API",
        description="API for interacting with the portal backend.",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(status_api, tags=["Status"])
    app.include_router(
        merchant_data_router,
        dependencies=[Depends(jwt_bearer)],
        prefix="/api/v1",
    )
    app.include_router(
        customer_wallet_router,
        dependencies=[Depends(jwt_bearer)],
        prefix="/api/v1",
    )

    app.mount("/fe2", StaticFiles(directory="fe2", html=True), name="Frontend 2")

    @app.exception_handler(Exception)
    async def generic_error_handler(_request: Request, ex: Exception) -> JSONResponse:
        """Handles generic exceptions."""
        return error_response(ex)

    @app.exception_handler(OSError)
    async def os_error_handler(_request: Request, ex: OSError) -> JSONResponse:
        """Handles OSErrors, usually caused by connection failure to other services."""
        return error_response(
            ex,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=(
                "Unable to process request due to connection failure to another "
                "service."
            ),
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
