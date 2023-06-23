"""API authentication dependencies."""
import datetime
from enum import Enum
from typing import Any, Callable, cast
from urllib.parse import urljoin
import jwt
from piccolo.columns import Column
import sentry_sdk
from fastapi import BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from bullsquid.service.auth0 import Auth0ServiceInterface
from bullsquid.settings import settings
from bullsquid.user_data.tables import UserProfile

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


class AccessLevel(str, Enum):
    """
    Defines a level of access to the application.
    """

    READ_ONLY = "ro"
    READ_WRITE = "rw"
    READ_WRITE_DELETE = "rwd"

    def role_name(self, app_name: str) -> str:
        """
        Returns the role name for this access level.
        This role name will match those present in the `permissions` claim of an
        Auth0 RBAC-enabled JWT.
        """
        return f"{app_name}:{self.value}"


def role_to_access_level(role: str, *, app_name: str) -> AccessLevel:
    """
    Valides the given role string and, if possible, returns the ``AccessLevel``
    it represents.

    >>> role_to_access_level("merchant_data:rwd", app_name="merchant_data")
    <AccessLevel.READ_WRITE_DELETE: 'rwd'>

    >>> role_to_access_level("badrole", app_name="merchant_data")
    ValueError: Roles must start with "app_name:", in this case "merchant_data:"

    >>> role_to_access_level("merchant_data:badrole", app_name="merchant_data")
    ValueError: 'badrole' is not a valid AccessLevel
    """
    prefix = f"{app_name}:"
    if not role.startswith(prefix):
        raise ValueError('Roles must start with "app_name:", in this case "{prefix}"')

    role = role[len(prefix) :]

    return AccessLevel(role)


def decode_jwt(token: str) -> dict:
    """
    Decodes the given JWT token string.
    Returns the token's contents.
    Raises a 401 Unauthorized HTTPException if the token fails validation or
    the signing key cannot be found.
    """
    if settings.api_key is not None:
        logger.warning(
            "Falling back on legacy token authentication. "
            "This is much less secure than OAuth2 and should not be relied upon "
            "in production!"
        )

        if token != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key"
            )

        return {
            "sub": "legacy-api-key-user",
            "permissions": [
                level.role_name(app_name)
                for app_name in ("merchant_data", "customer_wallet")
                for level in AccessLevel
            ],
        }

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
            detail=f"Authentication failed: {ex!r}",
        ) from ex


class JWTCredentials(HTTPAuthorizationCredentials):
    """
    Adds a claims dictionary to HTTPAuthorizationCredentials.
    This allows us to check claims in dependents of jwt_bearer.
    """

    claims: dict


class JWTBearer(HTTPBearer):
    """
    FastAPI view dependency providing JWT header validation and verification.
    """

    def __init__(self) -> None:
        super().__init__(auto_error=True)

    async def __call__(self, request: Request) -> JWTCredentials | None:
        credentials = await super().__call__(request)

        # when auto_error is true, credentials can never be null.
        assert credentials is not None

        if not (payload := decode_jwt(credentials.credentials)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        return JWTCredentials(
            scheme=credentials.scheme,
            credentials=credentials.credentials,
            claims=payload,
        )


jwt_bearer: Callable
if settings.debug or settings.oauth.domain is None:
    warning_parts = ["AUTH IS DISABLED! "]
    if settings.debug:
        warning_parts.append("Debug mode (settings.debug) is enabled")
    elif settings.oauth.domain is None:
        warning_parts.append("settings.oauth.domain is null")
    warning_parts.append(", so no authentication will be used.")
    logger.warning("".join(warning_parts))

    def jwt_bearer() -> JWTCredentials:
        """A fake jwt_bearer dependency for use in debug mode."""
        return JWTCredentials(scheme="Debug", credentials="", claims={})

else:
    jwt_bearer = JWTBearer()


async def fetch_user_data(user_id: str, auth0: Auth0ServiceInterface) -> None:
    profile_data = await auth0.get_user_profile(user_id)

    profile_fields: dict[Column, Any] = {
        UserProfile.email_address: profile_data["email"],
        UserProfile.name: profile_data["name"],
        UserProfile.nickname: profile_data["nickname"],
        UserProfile.picture: profile_data["picture"],
    }

    lookup = await UserProfile.objects().get_or_create(
        UserProfile.user_id == user_id,
        defaults=profile_fields,
    )
    created = lookup._was_created or False

    update_cutoff = datetime.datetime.utcnow() - settings.user_profile_ttl

    if not created and lookup.updated_at < update_cutoff:
        await UserProfile.update(cast(dict[Column | str, Any], profile_fields)).where(
            UserProfile.user_id == user_id
        )


_auth0: Auth0ServiceInterface | None = None


def require_access_level(
    level: AccessLevel, *, app_name: str
) -> Callable[[BackgroundTasks, JWTCredentials], JWTCredentials]:
    """
    FastAPI dependency that ensures a given access level exists in the client's
    access token.
    """

    def check_credentials(
        background_tasks: BackgroundTasks,
        credentials: JWTCredentials = Depends(jwt_bearer),
    ) -> JWTCredentials:
        if credentials.scheme != "Bearer":
            # we don't check permissions for non-bearer tokens.
            return credentials

        if level.role_name(app_name) not in credentials.claims["permissions"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing required permissions.",
            )

        global _auth0
        if _auth0 is None:
            _auth0 = Auth0ServiceInterface(cast(str, settings.oauth.domain))

        background_tasks.add_task(fetch_user_data, credentials.claims["sub"], _auth0)

        return credentials

    return check_credentials
