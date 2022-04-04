"""Application status API containing liveness and readiness checks."""
from fastapi import APIRouter, Response
from piccolo.engine import engine_finder

from bullsquid.status.models import ReadinessResult

router = APIRouter()


@router.get("/livez", status_code=204, response_class=Response)
async def liveness_check() -> None:
    """Liveness check. Returns 204 No Content if the server is alive."""


@router.get("/readyz", status_code=200, response_model=ReadinessResult)
async def readiness_check() -> dict:
    """
    Readiness check. Returns 200 OK if all required services are reachable,
    and the server is ready to serve requests.
    """
    engine = engine_finder()
    if not engine:
        raise RuntimeError("No database engine found")

    await engine.check_version()
    return {
        "status": "ok",
        "services": {
            "postgres": await engine.get_version(),
        },
    }