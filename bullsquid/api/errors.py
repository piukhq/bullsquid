"""Defines the base error types used by the API."""

from fastapi import HTTPException


class APIError(HTTPException):
    """Base class for all API errors."""

    status_code = 500
    error = "api_error.generic"
    message = "An error occurred while processing your request."

    def __init__(self) -> None:
        """Initialize the exception."""
        super().__init__(
            status_code=self.status_code,
            detail=[{"msg": self.message, "type": self.error}],
        )
