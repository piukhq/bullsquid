"""Database access layer."""
from typing import Any, Mapping

from bullsquid.merchant_data.tables import Merchant, PaymentScheme, Plan


class NoSuchRecord(Exception):
    """Raised when the requested record could not be found."""


async def get_plan(pk: str) -> Plan:
    """Return a plan by its primary key. Raises NoSuchRecord if `pk` is not found."""
    plan = await Plan.objects().get(Plan.pk == pk)
    if not plan:
        raise NoSuchRecord
    return plan


async def list_plans() -> list[Plan]:
    """Return a list of all plans."""
    return await Plan.objects()


async def create_plan(fields: Mapping[str, Any]) -> Plan:
    """Create a new plan with the given fields."""
    plan = Plan(**fields)
    await plan.save()
    return plan


async def update_plan(pk: str, fields: Mapping[str, Any]) -> Plan:
    """Update an existing merchant with the given fields."""
    plan = await get_plan(pk)
    for key, value in fields.items():
        setattr(plan, key, value)
    await plan.save()
    return plan


async def get_merchant(pk: str, *, plan_ref: str) -> Merchant:
    """Return a merchant by its primary key. Raises NoSuchRecord if `pk` is not found."""
    merchant = (
        await Merchant.objects()
        .where(Merchant.pk == pk, Merchant.plan == plan_ref)
        .first()
    )
    if not merchant:
        raise NoSuchRecord
    return merchant


async def list_merchants() -> list[Merchant]:
    """Return a list of all merchants."""
    return await Merchant.objects()


async def create_merchant(fields: Mapping[str, Any], *, plan: Plan) -> Merchant:
    """Create a new merchant with the given fields."""
    merchant = Merchant(**fields, plan=plan)
    await merchant.save()
    return merchant


async def update_merchant(
    pk: str, fields: Mapping[str, Any], *, plan_ref: str
) -> Merchant:
    """Update an existing merchant with the given fields."""
    merchant = await get_merchant(pk, plan_ref=plan_ref)
    for key, value in fields.items():
        setattr(merchant, key, value)
    await merchant.save()
    return merchant


async def delete_merchant(pk: str, *, plan_ref: str) -> None:
    """Delete a merchant by its primary key. Raises NoSuchRecord if `pk` is not found."""
    merchant = await get_merchant(pk, plan_ref=plan_ref)
    await merchant.remove()


async def list_payment_schemes() -> list[PaymentScheme]:
    """Return a list of all payment schemes."""
    return await PaymentScheme.objects()
