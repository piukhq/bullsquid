"""Tests for the Identifier/PSIMI database layer."""

from uuid import uuid4

from ward import raises, test

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.identifiers.db import get_identifier
from bullsquid.merchant_data.identifiers.tables import Identifier
from tests.fixtures import database
from tests.merchant_data.factories import identifier


@test("can get an identifier")
async def _(expected: Identifier = identifier) -> None:
    actual = await get_identifier(expected.pk)
    assert actual.pk == expected.pk


@test("attempting to get a non-existent identifier raises NoSuchRecord")
async def _(_db: None = database) -> None:
    with raises(NoSuchRecord):
        await get_identifier(uuid4())
