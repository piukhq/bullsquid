"""Application status API containing liveness and readiness checks."""

from fastapi import APIRouter, HTTPException, Response, status
from piccolo.apps.migrations.commands.check import (
    CheckMigrationManager,
    MigrationStatus,
)
from piccolo.engine import engine_finder

from bullsquid.status.models import ReadinessResult

router = APIRouter()


async def any_missing_migrations() -> list[MigrationStatus]:
    """Returns details of all migrations that have not yet run."""
    manager = CheckMigrationManager("all")
    statuses = await manager.get_migration_statuses()
    return [status for status in statuses if not status.has_ran]


@router.get("/livez", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def liveness_check() -> None:
    """Liveness check. Returns 204 No Content if the server is alive."""


@router.get("/readyz", status_code=status.HTTP_200_OK, response_model=ReadinessResult)
async def readiness_check() -> dict:
    """
    Readiness check. Returns 200 OK if all required services are reachable,
    the database schema is up to date, and the server is ready to serve requests.
    """
    engine = engine_finder()
    if not engine:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"msg": "No database engine found"},
        )

    await engine.check_version()

    if migrations := await any_missing_migrations():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "msg": "Some migrations have not yet run.",
                "migrations": [
                    {
                        "app_name": migration.app_name,
                        "migration_id": migration.migration_id,
                        "description": migration.description,
                    }
                    for migration in migrations
                ],
            },
        )

    return {
        "status": "ok",
        "services": {
            "postgres": await engine.get_version(),
        },
    }
