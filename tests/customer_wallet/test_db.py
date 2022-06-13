"""Test the customer wallet database access layer."""
import random
import secrets
from datetime import timezone

from piccolo.utils.encoding import load_json
from ward import test

from bullsquid.customer_wallet.db import list_user_lookups, upsert_user_lookup
from bullsquid.customer_wallet.tables import UserLookup
from tests.customer_wallet.factories import (
    three_user_lookups,
    user_lookup,
    user_lookup_factory,
)
from tests.fixtures import database


@test("upserting a new user lookup adds it to the database")
async def _(_db: None = database) -> None:
    auth_id = secrets.token_urlsafe()
    user_id = str(random.randint(1000000, 9999999))

    assert not await UserLookup.exists().where(
        UserLookup.auth_id == auth_id, UserLookup.user_id == user_id
    )

    lookups = await upsert_user_lookup(
        auth_id,
        user_id=user_id,
        channel="test-channel",
        display_text="test display text",
        lookup_type="jwt",
        criteria="test-token",
    )

    lookup = (
        await UserLookup.select(UserLookup.updated_at)
        .where(UserLookup.auth_id == auth_id, UserLookup.user_id == user_id)
        .first()
    )
    assert lookup is not None
    assert lookups == [
        {
            "user_id": user_id,
            "channel": "test-channel",
            "display_text": "test display text",
            "lookup_type": "jwt",
            "criteria": "test-token",
            "updated_at": lookup["updated_at"],
        },
    ]


@test("upserting an existing user lookup updates the lookup info and not the user info")
async def _(user_lookup: UserLookup = user_lookup) -> None:
    lookups = await upsert_user_lookup(
        user_lookup.auth_id,
        user_id=user_lookup.user_id,
        channel="new-channel",
        display_text="new-display-text",
        lookup_type="new-type",
        criteria="new-criteria",
    )

    updated_lookup = (
        await UserLookup.select(UserLookup.updated_at)
        .where(
            UserLookup.auth_id == user_lookup.auth_id,
            UserLookup.user_id == user_lookup.user_id,
        )
        .first()
    )
    assert updated_lookup is not None
    assert lookups == [
        {
            "user_id": user_lookup.user_id,
            "channel": user_lookup.channel,
            "display_text": user_lookup.display_text,
            "lookup_type": "new-type",
            "criteria": "new-criteria",
            "updated_at": updated_lookup["updated_at"],
        },
    ]

    assert updated_lookup["updated_at"] > user_lookup.updated_at.replace(
        tzinfo=timezone.utc
    )


@test("upserting an old lookup moves it to the top")
async def _(user_lookup: UserLookup = user_lookup) -> None:
    new_lookup = await user_lookup_factory(auth_id=user_lookup.auth_id)

    assert await list_user_lookups(user_lookup.auth_id) == [
        {
            "user_id": new_lookup.user_id,
            "channel": new_lookup.channel,
            "display_text": new_lookup.display_text,
            "lookup_type": new_lookup.lookup_type,
            "criteria": load_json(new_lookup.criteria),
            "updated_at": new_lookup.updated_at.replace(tzinfo=timezone.utc),
        },
        {
            "user_id": user_lookup.user_id,
            "channel": user_lookup.channel,
            "display_text": user_lookup.display_text,
            "lookup_type": user_lookup.lookup_type,
            "criteria": load_json(user_lookup.criteria),
            "updated_at": user_lookup.updated_at.replace(tzinfo=timezone.utc),
        },
    ]

    # now upsert the original lookup
    await upsert_user_lookup(
        user_lookup.auth_id,
        user_id=user_lookup.user_id,
        channel=user_lookup.channel,
        display_text=user_lookup.display_text,
        lookup_type=user_lookup.lookup_type,
        criteria=load_json(user_lookup.criteria),
    )

    lookup = (
        await UserLookup.select(UserLookup.updated_at)
        .where(
            UserLookup.auth_id == user_lookup.auth_id,
            UserLookup.user_id == user_lookup.user_id,
        )
        .first()
    )

    assert await list_user_lookups(user_lookup.auth_id) == [
        {
            "user_id": user_lookup.user_id,
            "channel": user_lookup.channel,
            "display_text": user_lookup.display_text,
            "lookup_type": user_lookup.lookup_type,
            "criteria": load_json(user_lookup.criteria),
            "updated_at": lookup["updated_at"],
        },
        {
            "user_id": new_lookup.user_id,
            "channel": new_lookup.channel,
            "display_text": new_lookup.display_text,
            "lookup_type": new_lookup.lookup_type,
            "criteria": load_json(new_lookup.criteria),
            "updated_at": new_lookup.updated_at.replace(tzinfo=timezone.utc),
        },
    ]


@test("can limit the number of lookups returned")
async def _(_db: None = database) -> None:
    auth_id = secrets.token_urlsafe()

    lookups = [await user_lookup_factory(auth_id=auth_id) for _ in range(5)]
    lookups.sort(key=lambda l: l.updated_at, reverse=True)

    results = await list_user_lookups(auth_id, n=2)
    assert results == [
        {
            "user_id": lookup.user_id,
            "channel": lookup.channel,
            "display_text": lookup.display_text,
            "lookup_type": lookup.lookup_type,
            "criteria": load_json(lookup.criteria),
            "updated_at": lookup.updated_at.replace(tzinfo=timezone.utc),
        }
        for lookup in lookups[:2]
    ]


@test("can limit & offset the number of lookups returned")
async def _(_db: None = database) -> None:
    auth_id = secrets.token_urlsafe()

    lookups = [await user_lookup_factory(auth_id=auth_id) for _ in range(5)]
    lookups.sort(key=lambda l: l.updated_at, reverse=True)

    results = await list_user_lookups(auth_id, n=2, p=2)
    assert results == [
        {
            "user_id": lookup.user_id,
            "channel": lookup.channel,
            "display_text": lookup.display_text,
            "lookup_type": lookup.lookup_type,
            "criteria": load_json(lookup.criteria),
            "updated_at": lookup.updated_at.replace(tzinfo=timezone.utc),
        }
        for lookup in lookups[4:6]
    ]
