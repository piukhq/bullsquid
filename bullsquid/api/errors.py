"""Defines the base error types used by the API."""

import sentry_sdk
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from loguru import logger

from settings import settings


def error_response(
    ex: Exception,
    *,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    message: str = "Unable to process request due to an internal error.",
) -> JSONResponse:
    """
    Logs the given exception to stdout (debug mode only), and sentry (if configured.)
    Returns a JSONResponse with the given status code and message, plus the sentry event ID.
    """
    if settings.debug:
        logger.exception(ex)

    event_id = sentry_sdk.capture_exception(ex)

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": {
                "msg": message,
                "event_id": event_id,
            }
        },
    )


class APIError(HTTPException):
    """Base class for all API errors."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error = "api_error"
    message = "An error occurred while processing your request."
    loc: list[str] | None = None

    def __init__(self) -> None:
        """Initialize the exception."""
        super().__init__(
            status_code=self.status_code,
            detail=[self.dict()],
        )

    def dict(self) -> dict:
        """Return the error details as a dictionary."""
        return {"loc": self.loc, "msg": self.message, "type": self.error}


class APIMultiError(HTTPException):
    """Allows raising multiple errors in one response."""

    def __init__(self, errors: list[APIError]) -> None:
        """Initialize the exception."""
        super().__init__(
            status_code=errors[0].status_code,
            detail=[error.dict() for error in errors],
        )


class ResourceNotFoundError(APIError):
    """Raised when the requested resource does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    error = "ref_error"

    def __init__(self, *, loc: list[str], resource_name: str) -> None:
        self.loc = loc
        self.message = f"{resource_name} not found."
        super().__init__()


class UniqueError(APIError):
    """Raised when a field is not unique."""

    status_code = status.HTTP_409_CONFLICT
    error = "unique_error"

    def __init__(self, *, loc: list[str]) -> None:
        self.loc = loc
        self.message = f"Field must be unique: {'.'.join(loc)}."
        super().__init__()
