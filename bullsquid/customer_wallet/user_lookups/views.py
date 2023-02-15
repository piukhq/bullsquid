"""Customer wallet API endpoints."""
from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from bullsquid.api.auth import AccessLevel, JWTCredentials
from bullsquid.customer_wallet.auth import require_access_level
from bullsquid.customer_wallet.user_lookups import db
from bullsquid.customer_wallet.user_lookups.models import (
    UserLookupRequest,
    UserLookupResponse,
)

router = APIRouter(prefix="/user_lookups")


@router.get("", response_model=list[UserLookupResponse])
async def list_user_lookups(
    user: str = Header(),
    n: int = Query(default=5),
    p: int = Query(default=1),
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> list[UserLookupResponse]:
    """List user lookups for the given user header."""
    return await db.list_user_lookups(user, n=n, p=p)


@router.put(
    "",
    responses={
        status.HTTP_200_OK: {"model": list[UserLookupResponse]},
        status.HTTP_201_CREATED: {"model": list[UserLookupResponse]},
    },
)
async def upsert_user_lookup(
    user_lookup: UserLookupRequest,
    user: str = Header(),
    n: int = Query(default=5),
    p: int = Query(default=1),
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> JSONResponse:
    """Upsert a user lookup for the given user header."""
    results, created = await db.upsert_user_lookup(
        fields=user_lookup,
        auth_id=user,
        n=n,
        p=p,
    )

    content = jsonable_encoder(results)
    return JSONResponse(
        content=content,
        status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )
