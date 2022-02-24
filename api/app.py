"""
Defines the create_app function used to initialize the application.
"""
from fastapi import FastAPI
from piccolo.engine import engine_finder

from mids.api.routers import v1 as mids_v1


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""

    app = FastAPI(
        title="Portal API",
        description="API for interacting with the portal backend.",
        version="1.0.0",
    )
    app.include_router(mids_v1, prefix="/mid_management", tags=["MID Management"])

    @app.on_event("startup")
    async def open_database_connection_pool() -> None:
        """Opens the database connection pool on application startup."""
        try:
            engine = engine_finder()
            if not engine:
                raise RuntimeError("No database engine found")
            await engine.start_connection_pool()
        except Exception as ex:  # pylint: disable=broad-except
            print(f"Unable to connect to the database: {ex}")

    @app.on_event("shutdown")
    async def close_database_connection_pool() -> None:
        """Closes the database connection pool on application shutdown."""
        try:
            engine = engine_finder()
            if not engine:
                raise RuntimeError("No database engine found")
            await engine.close_connection_pool()
        except Exception as ex:  # pylint: disable=broad-except
            print(f"Unable to connect to the database: {ex}")

    return app
