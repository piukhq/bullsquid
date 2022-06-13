"""Customer wallet API endpoints."""
from fastapi import APIRouter, Header, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from .db import UserLookupResult, upsert_user_lookup
from .models import LookupResponse, User, UserLookupRequest, UserLookupResponse

router = APIRouter(prefix="/user_lookups")


def make_user_lookup_response(result: UserLookupResult) -> UserLookupResponse:
    """Turns the result of a user lookup query into an API response."""
    return UserLookupResponse(
        user=User(
            user_id=result["user_id"],
            channel=result["channel"],
            display_text=result["display_text"],
        ),
        lookup=LookupResponse(
            type=result["lookup_type"],
            criteria=result["criteria"],
            datetime=result["updated_at"],
        ),
    )


@router.put(
    "",
    responses={
        status.HTTP_200_OK: {"model": list[UserLookupResponse]},
        status.HTTP_201_CREATED: {"model": list[UserLookupResponse]},
    },
)
async def _(
    user_lookup: UserLookupRequest,
    user: str = Header(),
    n: int = Query(default=5),
    p: int = Query(default=1),
) -> JSONResponse:
    results, created = await upsert_user_lookup(
        user,
        user_id=user_lookup.user.user_id,
        channel=user_lookup.user.channel,
        display_text=user_lookup.user.display_text,
        lookup_type=user_lookup.lookup.type,
        criteria=user_lookup.lookup.criteria,
        n=n,
        p=p,
    )

    content = jsonable_encoder(
        [make_user_lookup_response(result) for result in results]
    )
    return JSONResponse(
        content=content,
        status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )
