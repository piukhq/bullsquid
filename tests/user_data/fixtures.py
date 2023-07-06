from typing import Any
from piccolo.testing.model_builder import ModelBuilder
import pytest

from bullsquid.user_data.tables import UserProfile
from tests.helpers import Factory


@pytest.fixture
def user_profile_factory(database: None) -> Factory[UserProfile]:
    async def factory(*, persist: bool = True, **defaults: Any) -> UserProfile:
        result: UserProfile = await ModelBuilder.build(
            UserProfile,
            defaults=defaults,  # type: ignore
            persist=persist,
        )
        return result

    return factory
