"""Database access layer for operations on merchants."""

from typing import Any, Mapping
from uuid import UUID

from bullsquid.merchant_data.db import NoSuchRecord
from bullsquid.merchant_data.plans.tables import Plan

from .tables import Merchant


async def get_merchant(pk: UUID, *, plan_ref: UUID) -> Merchant:
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


async def count_merchants(plan_ref: UUID) -> int:
    """Return a count of merchants in a plan."""
    return await Merchant.count().where(Merchant.plan == plan_ref)


async def create_merchant(fields: Mapping[str, Any], *, plan: Plan) -> Merchant:
    """Create a new merchant with the given fields."""
    merchant = Merchant(**fields, plan=plan)
    await merchant.save()
    return merchant


async def update_merchant(
    pk: UUID, fields: Mapping[str, Any], *, plan_ref: UUID
) -> Merchant:
    """Update an existing merchant with the given fields."""
    merchant = await get_merchant(pk, plan_ref=plan_ref)
    for key, value in fields.items():
        setattr(merchant, key, value)
    await merchant.save()
    return merchant


async def delete_merchant(pk: UUID, *, plan_ref: UUID) -> None:
    """Delete a merchant by its primary key. Raises NoSuchRecord if `pk` is not found."""
    merchant = await get_merchant(pk, plan_ref=plan_ref)
    await merchant.remove()
