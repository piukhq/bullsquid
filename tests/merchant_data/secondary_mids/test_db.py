"""Tests for the secondary MIDs database layer."""

from uuid import uuid4

from ward import raises, test

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.secondary_mids.db import get_secondary_mid
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from tests.factories import secondary_mid
from tests.fixtures import database


@test("can get a secondary MID")
async def _(expected: SecondaryMID = secondary_mid) -> None:
    actual = await get_secondary_mid(expected.pk)
    assert actual.pk == expected.pk


@test("attempting to get a non-existent secondary MID raises NoSuchRecord")
async def _(_db: None = database) -> None:
    with raises(NoSuchRecord):
        await get_secondary_mid(uuid4())
