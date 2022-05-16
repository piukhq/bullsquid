"""Test the merchant data API database layer."""
from uuid import uuid4

from ward import raises, test

from bullsquid.merchant_data import db
from bullsquid.merchant_data.tables import Plan
from tests.factories import plan, three_plans
from tests.fixtures import database


@test("can get a plan by primary key")
async def _(_db: None = database, expected: Plan = plan) -> None:
    actual = await db.get_plan(expected.pk)
    assert actual.pk == expected.pk


@test("getting a plan that doesn't exist raises NoSuchRecord")
async def _(_db: None = database) -> None:
    with raises(db.NoSuchRecord):
        await db.get_plan(uuid4())


@test("can list all plans in an empty database")
async def _(_db: None = database) -> None:
    plans = await db.list_plans()
    assert len(plans) == 0


@test("can list all plans in a populated database")
async def _(
    _db: None = database,
    _plans: list[Plan] = three_plans,
) -> None:
    plans = await db.list_plans()
    assert len(plans) == 3


@test("can create a plan")
async def _(_db: None = database) -> None:
    plan = await db.create_plan({"name": "test"})
    plan = await db.get_plan(plan.pk)
    assert plan.name == "test"


@test("can update a plan")
async def _(_db: None = database, plan: Plan = plan) -> None:
    await db.update_plan(plan.pk, {"name": "updated"})
    plan = await db.get_plan(plan.pk)
    assert plan.name == "updated"


@test("updating a plan that doesn't exist raises NoSuchRecord")
async def _(_db: None = database) -> None:
    with raises(db.NoSuchRecord):
        await db.update_plan(uuid4(), {"name": "updated"})
