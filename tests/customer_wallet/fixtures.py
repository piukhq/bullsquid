"""Fixtures & factory functions for building customer wallet objects."""

import json
from datetime import datetime, timezone
from typing import Any

import pytest
from piccolo.testing.model_builder import ModelBuilder

from bullsquid.customer_wallet.user_lookups.tables import UserLookup
from tests.helpers import Factory


@pytest.fixture
def user_lookup_factory(database: None) -> Factory[UserLookup]:
    async def factory(*, persist: bool = True, **defaults: Any) -> UserLookup:
        result: UserLookup = await ModelBuilder.build(
            UserLookup,
            defaults={
                "updated_at": datetime.now(timezone.utc),
                **defaults,  # type: ignore
            },
            persist=persist,
        )
        result.criteria = json.loads(result.criteria)
        return result

    return factory
