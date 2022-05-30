"""Database access layer for plan operations."""
from typing import Any, Mapping
from uuid import UUID

from bullsquid.merchant_data.db import NoSuchRecord

from .tables import Plan


async def get_plan(pk: UUID) -> Plan:
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


async def update_plan(pk: UUID, fields: Mapping[str, Any]) -> Plan:
    """Update an existing merchant with the given fields."""
    plan = await get_plan(pk)
    for key, value in fields.items():
        setattr(plan, key, value)
    await plan.save()
    return plan