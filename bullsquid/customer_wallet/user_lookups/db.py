"""Custom wallet database access layer."""
from datetime import datetime, timezone

from piccolo.utils.encoding import dump_json

from bullsquid.customer_wallet.user_lookups.models import (
    LookupResponse,
    User,
    UserLookupRequest,
    UserLookupResponse,
)
from bullsquid.customer_wallet.user_lookups.tables import UserLookup
from bullsquid.db import paginate


async def list_user_lookups(
    auth_id: str, *, n: int, p: int = 1
) -> list[UserLookupResponse]:
    """
    Get a list of user lookups for the given auth_id, sorted most recent to
    least recent.
    """
    lookups = await paginate(
        UserLookup.objects()
        .where(UserLookup.auth_id == auth_id)
        .order_by(UserLookup.updated_at, ascending=False),
        n=n,
        p=p,
    ).output(load_json=True)

    return [
        UserLookupResponse(
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
        for result in lookups
    ]


async def upsert_user_lookup(
    fields: UserLookupRequest,
    *,
    auth_id: str,
    n: int,
    p: int = 1,
) -> tuple[list[UserLookupResponse], bool]:
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
    criteria = dump_json(fields.lookup.criteria)

    # TODO: make a generic upsert function
    where = (UserLookup.auth_id == auth_id) & (
        UserLookup.user_id == fields.user.user_id
    )
    lookup = await UserLookup.objects().get_or_create(
        where,
        defaults={
            UserLookup.channel: fields.user.channel,
            UserLookup.display_text: fields.user.display_text,
            UserLookup.lookup_type: fields.lookup.type,
            UserLookup.criteria: criteria,
        },
    )
    created = lookup._was_created or False  # pylint: disable=protected-access
    if not created:
        await UserLookup.update(
            {
                UserLookup.lookup_type: fields.lookup.type,
                UserLookup.criteria: criteria,
                UserLookup.updated_at: datetime.now(timezone.utc),
            }
        ).where(where)

    return await list_user_lookups(auth_id, n=n, p=p), created
