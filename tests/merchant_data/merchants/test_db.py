"""Test the merchant data API database layer."""
from uuid import uuid4

from ward import raises, test

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.merchants.db import (
    create_merchant,
    delete_merchant,
    get_merchant,
    list_merchants,
    update_merchant,
)
from bullsquid.merchant_data.merchants.models import CreateMerchantRequest
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from tests.fixtures import database
from tests.merchant_data.factories import merchant, merchant_factory, plan


@test("can get a merchant by primary key")
async def _(merchant: Merchant = merchant) -> None:
    actual = await get_merchant(merchant.pk, plan_ref=merchant.plan)
    assert actual.pk == merchant.pk


@test("getting a merchant that doesn't exist raises NoSuchRecord")
async def _(plan: Plan = plan) -> None:
    with raises(NoSuchRecord):
        await get_merchant(uuid4(), plan_ref=plan.pk)


@test("getting a merchant from a plan that doesn't exist raises NoSuchRecord")
async def _(merchant: Merchant = merchant) -> None:
    with raises(NoSuchRecord):
        await get_merchant(merchant.pk, plan_ref=uuid4())


@test("getting a merchant from a plan it doesn't belong to raises NoSuchRecord")
async def _(plan: Plan = plan, merchant: Merchant = merchant) -> None:
    with raises(NoSuchRecord):
        await get_merchant(merchant.pk, plan_ref=plan.pk)


@test("can list all merchants in an empty database")
async def _(plan: Plan = plan) -> None:
    merchants = await list_merchants(plan.pk, n=10, p=1)
    assert len(merchants) == 0


@test("can list all merchants in a populated database")
async def _(plan: Plan = plan) -> None:
    await merchant_factory(plan=plan)
    await merchant_factory(plan=plan)
    await merchant_factory(plan=plan)

    merchants = await list_merchants(plan.pk, n=10, p=1)
    assert len(merchants) == 3


@test("listing merchants does not include deleted records")
async def _(plan: Plan = plan) -> None:
    await merchant_factory(plan=plan)
    await merchant_factory(plan=plan, status=ResourceStatus.DELETED)
    await merchant_factory(plan=plan)

    merchants = await list_merchants(plan.pk, n=10, p=1)
    assert len(merchants) == 2


@test("can't list merchants on a non-existent plan")
async def _(_db: None = database) -> None:
    with raises(NoSuchRecord):
        await list_merchants(uuid4(), n=10, p=1)


@test("can create a merchant")
async def _(plan: Plan = plan) -> None:
    merchant = await create_merchant({"name": "test"}, plan=plan)
    merchant = await get_merchant(merchant.pk, plan_ref=plan.pk)
    assert merchant.name == "test"


@test("can update a merchant")
async def _(merchant: Merchant = merchant) -> None:
    update = CreateMerchantRequest(name="updated", location_label="also updated")
    await update_merchant(
        merchant.pk,
        update,
        plan_ref=merchant.plan,
    )
    merchant = await get_merchant(merchant.pk, plan_ref=merchant.plan)
    assert merchant.name == "updated"
    assert merchant.location_label == "also updated"


@test("updating a merchant that doesn't exist raises NoSuchRecord")
async def _(plan: Plan = plan) -> None:
    update = CreateMerchantRequest(name="updated", location_label="also updated")
    with raises(NoSuchRecord):
        await update_merchant(uuid4(), update, plan_ref=plan.pk)


@test("updating a merchant on a plan that doesn't exist raises NoSuchRecord")
async def _(merchant: Merchant = merchant) -> None:
    update = CreateMerchantRequest(name="updated", location_label="also updated")
    with raises(NoSuchRecord):
        await update_merchant(merchant.pk, update, plan_ref=uuid4())


@test("updating a merchant on a plan it doesn't belong to raises NoSuchRecord")
async def _(plan: Plan = plan, merchant: Merchant = merchant) -> None:
    update = CreateMerchantRequest(name="updated", location_label="also updated")
    with raises(NoSuchRecord):
        await update_merchant(merchant.pk, update, plan_ref=plan.pk)


@test("can delete a merchant")
async def _(merchant: Merchant = merchant) -> None:
    await delete_merchant(merchant.pk, plan_ref=merchant.plan)
    with raises(NoSuchRecord):
        await get_merchant(merchant.pk, plan_ref=merchant.plan)


@test("deleting a merchant that doesn't exist raises NoSuchRecord")
async def _(plan: Plan = plan) -> None:
    with raises(NoSuchRecord):
        await delete_merchant(uuid4(), plan_ref=plan.pk)
