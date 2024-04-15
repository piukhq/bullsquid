"""Response models for the status API."""

from pydantic import BaseModel


class ReadinessResultServices(BaseModel):
    """
    Connected services returned in readiness check.
    """

    postgres: str


class ReadinessResult(BaseModel):
    """
    Readiness check result model.
    """

    status: str
    services: ReadinessResultServices
