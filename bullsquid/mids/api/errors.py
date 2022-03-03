"""Defines all the errors that can be thrown by the MIDs API."""
from starlette.status import HTTP_404_NOT_FOUND

from bullsquid.api.errors import APIError


class MerchantNotFoundError(APIError):
    """Raised when the merchant requested does not exist."""

    status_code = HTTP_404_NOT_FOUND
    error = "ref_error.merchant"
    message = "Merchant not found."
