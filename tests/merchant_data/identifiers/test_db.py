"""Tests for the Identifier/PSIMI database layer."""

from uuid import uuid4

from ward import raises, test

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.identifiers.db import get_identifier
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from tests.fixtures import database
from tests.merchant_data.factories import (
    identifier,
    identifier_factory,
    merchant_factory,
    plan_factory,
)


@test("can get an identifier")
async def _(_db: None = database) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    expected = await identifier_factory(merchant=merchant)
    actual = await get_identifier(
        expected.pk, plan_ref=plan.pk, merchant_ref=merchant.pk
    )
    assert actual["pk"] == expected.pk


@test("attempting to get a non-existent identifier raises NoSuchRecord")
async def _(_db: None = database) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    with raises(NoSuchRecord) as ex:
        await get_identifier(uuid4(), plan_ref=plan.pk, merchant_ref=merchant.pk)
    assert ex.raised.table == Identifier


@test("attempting to get an identifier from a non-existent plan raises NoSuchRecord")
async def _(_db: None = database) -> None:
    merchant = await merchant_factory()
    identifier = await identifier_factory(merchant=merchant)
    with raises(NoSuchRecord) as ex:
        await get_identifier(identifier.pk, plan_ref=uuid4(), merchant_ref=merchant.pk)
    assert ex.raised.table == Plan


@test(
    "attempting to get an identifier from a non-existent merchant raises NoSuchRecord"
)
async def _(_db: None = database) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(merchant=merchant)
    with raises(NoSuchRecord) as ex:
        await get_identifier(identifier.pk, plan_ref=plan.pk, merchant_ref=uuid4())
    assert ex.raised.table == Merchant
