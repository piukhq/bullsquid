"""API authentication dependencies."""
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from settings import settings

apikey_header = APIKeyHeader(name="Authorization")


def check_api_key(api_key: str = Depends(apikey_header)) -> None:
    """Checks the API key in the authentication header for validity."""
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key"
        )
