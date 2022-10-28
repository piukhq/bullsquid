"""Database access layer for operations on merchants."""

from typing import Any, Mapping
from uuid import UUID

from piccolo.columns import Column

from bullsquid.db import NoSuchRecord, paginate
from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.models import CreateMerchantRequest
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.db import get_plan
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID


async def get_merchant(
    pk: UUID, *, plan_ref: UUID | None, validate_plan: bool = True
) -> Merchant:
    """Return a merchant by its primary key. Raises NoSuchRecord if `pk` is not found."""

    query = Merchant.objects().where(Merchant.pk == pk)
    if validate_plan:
        if plan_ref is None:
            raise ValueError("validate_plan cannot be true if plan_ref is null")

        plan = await get_plan(plan_ref)
        query = query.where(Merchant.plan == plan)

    merchant = await query.first()

    if not merchant:
        raise NoSuchRecord(Merchant)

    return merchant


async def list_merchants(plan_ref: UUID, *, n: int, p: int) -> list[Merchant]:
    """Return a list of all merchants."""
    plan = await get_plan(plan_ref)
    return await paginate(
        Merchant.objects().where(Merchant.plan == plan.pk),
        n=n,
        p=p,
    )


async def create_merchant(fields: Mapping[str, Any], *, plan: Plan) -> Merchant:
    """Create a new merchant with the given fields."""
    merchant = Merchant(**fields, plan=plan)
    await merchant.save()
    return merchant


async def update_merchant(
    pk: UUID, fields: CreateMerchantRequest, *, plan_ref: UUID
) -> Merchant:
    """Update an existing merchant with the given fields."""
    merchant = await get_merchant(pk, plan_ref=plan_ref)
    for key, value in fields:
        setattr(merchant, key, value)
    await merchant.save()
    return merchant


async def merchant_has_onboarded_resources(pk: UUID) -> bool:
    """
    Returns true if the given merchant has any onboarded primary MIDs,
    secondary MIDs, or identifiers.
    """
    primary_mids = PrimaryMID.exists().where(
        PrimaryMID.merchant == pk, PrimaryMID.txm_status == TXMStatus.ONBOARDED
    )
    secondary_mids = SecondaryMID.exists().where(
        SecondaryMID.merchant == pk, SecondaryMID.txm_status == TXMStatus.ONBOARDED
    )
    identifiers = Identifier.exists().where(
        Identifier.merchant == pk, Identifier.txm_status == TXMStatus.ONBOARDED
    )

    return (await primary_mids) or (await secondary_mids) or (await identifiers)


async def update_merchant_status(
    pk: UUID, status: ResourceStatus, *, cascade: bool = False
) -> None:
    """
    Set the given merchant's status.
    If cascade = true, also update all associated resources.
    """
    async with Merchant._meta.db.transaction():  # pylint: disable=protected-access
        await Merchant.update({Merchant.status: status}).where(Merchant.pk == pk)
        if cascade:
            fields: dict[Column | str, Any] = {PrimaryMID.status: status}
            if status == ResourceStatus.DELETED:
                fields[PrimaryMID.location] = None

            await PrimaryMID.update(fields).where(PrimaryMID.merchant == pk)
            await SecondaryMID.update({SecondaryMID.status: status}).where(
                SecondaryMID.merchant == pk
            )
            await Identifier.update({Identifier.status: status}).where(
                Identifier.merchant == pk
            )
            await Location.update({Location.status: status}).where(
                Location.merchant == pk
            )
            if status == ResourceStatus.DELETED:
                link_refs = (
                    await SecondaryMIDLocationLink.select(SecondaryMIDLocationLink.pk)
                    .where(SecondaryMIDLocationLink.secondary_mid.merchant == pk)
                    .output(as_list=True)
                )
                if link_refs:
                    await SecondaryMIDLocationLink.delete().where(
                        SecondaryMIDLocationLink.pk.is_in(link_refs)
                    )
