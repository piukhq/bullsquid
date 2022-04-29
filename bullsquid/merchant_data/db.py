"""Database access layer."""
from typing import Any, Mapping

from bullsquid.merchant_data.tables import Location, Merchant, Plan


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


async def get_merchant(pk: str) -> Merchant:
    """Return a merchant by its primary key. Raises NoSuchRecord if `pk` is not found."""
    merchant = await Merchant.objects().get(Merchant.pk == pk)
    if not merchant:
        raise NoSuchRecord
    return merchant


async def list_merchants() -> list[Merchant]:
    """Return a list of all merchants."""
    return await Merchant.objects()


async def create_merchant(fields: Mapping[str, Any]) -> Merchant:
    """Create a new merchant with the given fields."""
    merchant = Merchant(**fields)
    await merchant.save()
    return merchant


async def update_merchant(pk: str, fields: Mapping[str, Any]) -> Merchant:
    """Update an existing merchant with the given fields."""
    merchant = await get_merchant(pk)
    for key, value in fields.items():
        setattr(merchant, key, value)
    await merchant.save()
    return merchant


async def delete_merchant(pk: str) -> None:
    """Delete a merchant by its primary key. Raises NoSuchRecord if `pk` is not found."""
    merchant = await get_merchant(pk)
    await merchant.remove()


async def get_location(pk: str, *, merchant: Merchant) -> Location:
    """
    Return a location by its primary key. Raises NoSuchRecord if `pk` is not found.
    Additionally validates that the location belongs to the given merchant.
    """
    location = (
        await Location.objects()
        .where(Location.pk == pk, Location.merchant == merchant)
        .first()
    )
    if not location:
        raise NoSuchRecord

    return location


async def create_location(fields: Mapping[str, Any], *, merchant: Merchant) -> Location:
    """Create a new merchant with the given fields."""
    location = Location(**fields, merchant=merchant)
    await location.save()
    return location


async def update_location(
    pk: str, fields: Mapping[str, Any], *, merchant: Merchant
) -> Location:
    """Update an existing location with the given fields."""
    location = await get_location(pk, merchant=merchant)
    for key, value in fields.items():
        setattr(location, key, value)
    await location.save()
    return location
