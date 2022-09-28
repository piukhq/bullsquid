"""Database access layer for plan operations."""
from typing import Any, Mapping
from uuid import UUID

from bullsquid.db import NoSuchRecord, paginate
from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID


async def get_plan(pk: UUID) -> Plan:
    """Return a plan by its primary key. Raises NoSuchRecord if `pk` is not found."""
    plan = await Plan.objects().get(Plan.pk == pk)
    if not plan:
        raise NoSuchRecord(Plan)
    return plan


async def list_plans(*, n: int, p: int) -> list[Plan]:
    """Return a list of all plans."""
    return await paginate(
        Plan.objects().where(Plan.status != ResourceStatus.DELETED),
        n=n,
        p=p,
    )


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


async def plan_has_onboarded_resources(pk: UUID) -> bool:
    """
    Returns true if the given plan has any onboarded primary MIDs,
    secondary MIDs, or identifiers.
    """
    primary_mids = PrimaryMID.exists().where(
        PrimaryMID.merchant.plan == pk, PrimaryMID.txm_status == TXMStatus.ONBOARDED
    )
    secondary_mids = SecondaryMID.exists().where(
        SecondaryMID.merchant.plan == pk, SecondaryMID.txm_status == TXMStatus.ONBOARDED
    )
    identifiers = Identifier.exists().where(
        Identifier.merchant.plan == pk, Identifier.txm_status == TXMStatus.ONBOARDED
    )

    return (await primary_mids) or (await secondary_mids) or (await identifiers)


async def update_plan_status(
    pk: UUID, status: ResourceStatus, *, cascade: bool = False
) -> None:
    """
    Set the given plan's status.
    If cascade = true, also update all associated resources.
    """
    async with Plan._meta.db.transaction():  # pylint: disable=protected-access
        await Plan.update({Plan.status: status}).where(Plan.pk == pk)

        if cascade:
            await Merchant.update({Merchant.status: status}).where(Merchant.plan == pk)

            # temporary workaround for joins not being supported in updates.
            # https://github.com/piccolo-orm/piccolo/issues/625
            # TODO: remove when piccolo is updated.
            merchant_refs = (
                await Merchant.select(Merchant.pk)
                .where(Merchant.plan == pk)
                .output(as_list=True)
            )

            await PrimaryMID.update({PrimaryMID.status: status}).where(
                PrimaryMID.merchant.is_in(merchant_refs)
            )
            await SecondaryMID.update({SecondaryMID.status: status}).where(
                SecondaryMID.merchant.is_in(merchant_refs)
            )
            await Identifier.update({Identifier.status: status}).where(
                Identifier.merchant.is_in(merchant_refs)
            )
            await Location.update({Location.status: status}).where(
                Location.merchant.is_in(merchant_refs)
            )
