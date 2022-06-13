"""Custom wallet database access layer."""
from datetime import datetime, timezone
from typing import Any, TypedDict

from piccolo.utils.encoding import dump_json

from bullsquid.db import paginate

from .tables import UserLookup


class UserLookupResult(TypedDict):
    """Structure returned by the user lookup functions."""

    user_id: str
    channel: str
    display_text: str
    lookup_type: str
    criteria: Any
    updated_at: datetime


async def list_user_lookups(
    auth_id: str, *, n: int, p: int = 1
) -> list[UserLookupResult]:
    """
    Get a list of user lookups for the given auth_id, sorted most recent to
    least recent.
    """
    return await paginate(
        UserLookup.select(
            UserLookup.user_id,
            UserLookup.channel,
            UserLookup.display_text,
            UserLookup.lookup_type,
            UserLookup.criteria,
            UserLookup.updated_at,
        )
        .where(UserLookup.auth_id == auth_id)
        .order_by(UserLookup.updated_at, ascending=False),
        n=n,
        p=p,
    ).output(load_json=True)


async def upsert_user_lookup(
    auth_id: str,
    *,
    user_id: str,
    channel: str,
    display_text: str,
    lookup_type: str,
    criteria: Any,
    n: int,
    p: int = 1,
) -> tuple[list[UserLookupResult], bool]:
    """
    Create or update a user lookup.

    auth_id is used to identify the user the lookup belongs to.

    User details (user_id, channel, display_text) are used on insert, but not on update.
    Lookup details (lookup_type, criteria) are updated on both insert and update.

    `n` and `p` are used to paginate the results.

    Returns the full list of user lookups as per `list_user_lookups(auth_id, n=n, p=p)`.
    Also returns a boolean indicating if a new record was created.
    """
    # piccolo will automatically serialize dicts and lists, but if you give a
    # string to a JSON field it assumes it's a JSON string already. since
    # `criteria` in this case can be anything, we dump the JSON ourselves here.
    criteria = dump_json(criteria)

    # TODO: make a generic upsert function
    where = (UserLookup.auth_id == auth_id) & (UserLookup.user_id == user_id)
    lookup = await UserLookup.objects().get_or_create(
        where,
        defaults={
            UserLookup.channel: channel,
            UserLookup.display_text: display_text,
            UserLookup.lookup_type: lookup_type,
            UserLookup.criteria: criteria,
        },
    )
    created = lookup._was_created  # pylint: disable=protected-access
    if not created:
        await UserLookup.update(
            {
                UserLookup.lookup_type: lookup_type,
                UserLookup.criteria: criteria,
                UserLookup.updated_at: datetime.now(timezone.utc),
            }
        ).where(where)

    return await list_user_lookups(auth_id, n=n, p=p), created
