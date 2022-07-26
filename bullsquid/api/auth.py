"""API authentication dependencies."""
from typing import Callable
from urllib.parse import urljoin

import jwt
import sentry_sdk
from fastapi import HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from settings import settings

apikey_header = APIKeyHeader(name="Authorization")

# the client will cache up to 16 keys by default, so we keep a global instance
# in order to make best use of that.
JWKS_CLIENT: jwt.PyJWKClient | None
if settings.oauth.domain:
    JWKS_CLIENT = jwt.PyJWKClient(
        urljoin(settings.oauth.domain, "/.well-known/jwks.json")
    )
else:
    JWKS_CLIENT = None


def verify_jwt(token: str) -> dict:
    """
    Verifies the given JWT token string.
    Returns the token's contents.
    Raises a 401 Unauthorized HTTPException if the token fails validation or
    the signing key cannot be found.
    """
    if JWKS_CLIENT is None:
        raise RuntimeError("OAuth must be configured when not running in debug mode.")

    try:
        key = JWKS_CLIENT.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            key,
            algorithms=settings.oauth.algorithms,
            options={"require": ["exp", "iat", "aud", "iss"]},
            audience=settings.oauth.audience,
            issuer=settings.oauth.domain,
            leeway=settings.oauth.leeway,
        )
    except Exception as ex:
        sentry_sdk.capture_exception()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {repr(ex)}",
        ) from ex


class JWTBearer(HTTPBearer):
    """
    FastAPI view dependency providing JWT header validation and verification.
    """

    def __init__(self) -> None:
        super().__init__(auto_error=True)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        credentials = await super().__call__(request)

        # when auto_error is true, credentials can never be null.
        assert credentials is not None

        if not verify_jwt(credentials.credentials):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        return credentials


jwt_bearer: Callable
if settings.debug:

    def jwt_bearer() -> HTTPAuthorizationCredentials:
        """A fake jwt_bearer dependency for use in debug mode."""
        return HTTPAuthorizationCredentials(scheme="Debug", credentials="")

else:
    jwt_bearer = JWTBearer()
