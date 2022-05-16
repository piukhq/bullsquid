"""Test the merchant data API database layer."""
from uuid import uuid4

from ward import raises, test

from bullsquid.merchant_data import db
from bullsquid.merchant_data.tables import Merchant, Plan
from tests.factories import merchant, plan, three_merchants
from tests.fixtures import database


@test("can get a merchant by primary key")
async def _(
    _db: None = database,
    merchant: Merchant = merchant,
) -> None:
    actual = await db.get_merchant(merchant.pk, plan_ref=merchant.plan)
    assert actual.pk == merchant.pk


@test("getting a merchant that doesn't exist raises NoSuchRecord")
async def _(_db: None = database, plan: Plan = plan) -> None:
    with raises(db.NoSuchRecord):
        await db.get_merchant(uuid4(), plan_ref=plan.pk)


@test("getting a merchant from a plan that doesn't exist raises NoSuchRecord")
async def _(_db: None = database, merchant: Merchant = merchant) -> None:
    with raises(db.NoSuchRecord):
        await db.get_merchant(merchant.pk, plan_ref=uuid4())


@test("getting a merchant from a plan it doesn't belong to raises NoSuchRecord")
async def _(
    _db: None = database, plan: Plan = plan, merchant: Merchant = merchant
) -> None:
    with raises(db.NoSuchRecord):
        await db.get_merchant(merchant.pk, plan_ref=plan.pk)


@test("can list all merchants in an empty database")
async def _(_db: None = database) -> None:
    merchants = await db.list_merchants()
    assert len(merchants) == 0


@test("can list all merchants in a populated database")
async def _(
    _db: None = database,
    _merchants: list[Merchant] = three_merchants,
) -> None:
    merchants = await db.list_merchants()
    assert len(merchants) == 3


@test("can create a merchant")
async def _(_db: None = database, plan: Plan = plan) -> None:
    merchant = await db.create_merchant({"name": "test"}, plan=plan)
    merchant = await db.get_merchant(merchant.pk, plan_ref=plan.pk)
    assert merchant.name == "test"


@test("can update a merchant")
async def _(_db: None = database, merchant: Merchant = merchant) -> None:
    await db.update_merchant(merchant.pk, {"name": "updated"}, plan_ref=merchant.plan)
    merchant = await db.get_merchant(merchant.pk, plan_ref=merchant.plan)
    assert merchant.name == "updated"


@test("updating a merchant that doesn't exist raises NoSuchRecord")
async def _(_db: None = database, plan: Plan = plan) -> None:
    with raises(db.NoSuchRecord):
        await db.update_merchant(uuid4(), {"name": "updated"}, plan_ref=plan.pk)


@test("updating a merchant on a plan that doesn't exist raises NoSuchRecord")
async def _(_db: None = database, merchant: Merchant = merchant) -> None:
    with raises(db.NoSuchRecord):
        await db.update_merchant(merchant.pk, {"name": "updated"}, plan_ref=uuid4())


@test("updating a merchant on a plan it doesn't belong to raises NoSuchRecord")
async def _(
    _db: None = database, plan: Plan = plan, merchant: Merchant = merchant
) -> None:
    with raises(db.NoSuchRecord):
        await db.update_merchant(merchant.pk, {"name": "updated"}, plan_ref=plan.pk)


@test("can delete a merchant")
async def _(_db: None = database, merchant: Merchant = merchant) -> None:
    await db.delete_merchant(merchant.pk, plan_ref=merchant.plan)
    with raises(db.NoSuchRecord):
        await db.get_merchant(merchant.pk, plan_ref=merchant.plan)


@test("deleting a merchant that doesn't exist raises NoSuchRecord")
async def _(_db: None = database, plan: Plan = plan) -> None:
    with raises(db.NoSuchRecord):
        await db.delete_merchant(uuid4(), plan_ref=plan.pk)
