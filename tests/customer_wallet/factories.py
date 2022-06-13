"""Fixtures & factory functions for building customer wallet objects."""
from datetime import datetime, timezone
from typing import Any, Mapping

from piccolo.testing.model_builder import ModelBuilder
from ward import fixture

from bullsquid.customer_wallet.user_lookups.tables import UserLookup
from tests.fixtures import database


async def user_lookup_factory(*, persist: bool = True, **defaults: Any) -> UserLookup:
    """Creates and returns a user lookup."""
    return await ModelBuilder.build(
        UserLookup,
        defaults={
            "updated_at": datetime.now(timezone.utc),
            **defaults,  # type: ignore
        },
        persist=persist,
    )


@fixture
async def user_lookup(_db: None = database) -> UserLookup:
    return await user_lookup_factory()


@fixture
async def three_user_lookups(_db: None = database) -> list[UserLookup]:
    return [await user_lookup_factory() for _ in range(3)]
