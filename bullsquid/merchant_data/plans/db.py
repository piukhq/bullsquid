"""Database access layer for plan operations."""

from typing import Any, Mapping
from uuid import UUID

from piccolo.columns import Column

from bullsquid.db import NoSuchRecord, paginate
from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.psimis.tables import PSIMI
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID


async def get_plan(pk: UUID) -> Plan:
    """Return a plan by its primary key. Raises NoSuchRecord if `pk` is not found."""
    plan = await Plan.objects().where(Plan.pk == pk).first()
    if not plan:
        raise NoSuchRecord(Plan)
    return plan


async def list_plans(*, n: int, p: int) -> list[Plan]:
    """Return a list of all plans."""
    return await paginate(Plan.objects(), n=n, p=p)


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
    secondary MIDs, or PSIMIs.
    """
    # small optimisation; if a plan has no merchants then it can't have any
    # onboarded resources.
    if not await Merchant.exists().where(Merchant.plan == pk):
        return False

    primary_mids = PrimaryMID.exists().where(
        PrimaryMID.merchant.plan == pk, PrimaryMID.txm_status == TXMStatus.ONBOARDED
    )
    secondary_mids = SecondaryMID.exists().where(
        SecondaryMID.merchant.plan == pk, SecondaryMID.txm_status == TXMStatus.ONBOARDED
    )
    psimis = PSIMI.exists().where(
        PSIMI.merchant.plan == pk, PSIMI.txm_status == TXMStatus.ONBOARDED
    )

    return (await primary_mids) or (await secondary_mids) or (await psimis)


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
            merchant_refs = (
                await Merchant.select(Merchant.pk)
                .where(Merchant.plan == pk)
                .output(as_list=True)
            )
            if not merchant_refs:
                # nothing more to do
                return

            await Merchant.update({Merchant.status: status}).where(Merchant.plan == pk)

            fields: dict[Column | str, Any] = {PrimaryMID.status: status}
            if status == ResourceStatus.DELETED:
                fields[PrimaryMID.location] = None
            await PrimaryMID.update(fields).where(
                PrimaryMID.merchant.is_in(merchant_refs)
            )

            await SecondaryMID.update({SecondaryMID.status: status}).where(
                SecondaryMID.merchant.is_in(merchant_refs)
            )
            await PSIMI.update({PSIMI.status: status}).where(
                PSIMI.merchant.is_in(merchant_refs)
            )
            await Location.update({Location.status: status}).where(
                Location.merchant.is_in(merchant_refs)
            )
            if status == ResourceStatus.DELETED:
                link_refs = (
                    await SecondaryMIDLocationLink.select(SecondaryMIDLocationLink.pk)
                    .where(
                        SecondaryMIDLocationLink.secondary_mid.merchant.is_in(
                            merchant_refs
                        )
                    )
                    .output(as_list=True)
                )
                if link_refs:
                    await SecondaryMIDLocationLink.delete().where(
                        SecondaryMIDLocationLink.pk.is_in(link_refs)
                    )
