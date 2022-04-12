"""API authentication dependencies."""
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from settings import settings

apikey_header = APIKeyHeader(name="Authorization")


def check_api_key(api_key: str = Depends(apikey_header)) -> None:
    """Checks the API key in the authentication header for validity."""
    try:
        prefix, key = api_key.split(maxsplit=1)
    except ValueError as ex:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be in the format: token <key>",
        ) from ex

    if prefix.lower() != "token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must begin with 'token'",
        )

    if key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )
