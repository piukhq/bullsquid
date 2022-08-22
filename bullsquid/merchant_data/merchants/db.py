"""Database access layer for operations on merchants."""

from typing import Any, Mapping
from uuid import UUID

from bullsquid.db import NoSuchRecord, paginate
from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.models import CreateMerchantRequest
from bullsquid.merchant_data.plans.db import get_plan
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID

from .tables import Merchant


async def get_merchant(pk: UUID, *, plan_ref: UUID) -> Merchant:
    """Return a merchant by its primary key. Raises NoSuchRecord if `pk` is not found."""

    plan = await get_plan(plan_ref)
    merchant = (
        await Merchant.objects()
        .where(
            Merchant.pk == pk,
            Merchant.plan == plan,
            Merchant.status != ResourceStatus.DELETED,
        )
        .first()
    )
    if not merchant:
        raise NoSuchRecord(Merchant)
    return merchant


async def list_merchants(plan_ref: UUID, *, n: int, p: int) -> list[Merchant]:
    """Return a list of all merchants."""
    plan = await get_plan(plan_ref)
    return await paginate(
        Merchant.objects().where(
            Merchant.plan == plan.pk, Merchant.status != ResourceStatus.DELETED
        ),
        n=n,
        p=p,
    )


async def count_merchants(plan_ref: UUID) -> int:
    """Return a count of merchants in a plan."""
    plan = await get_plan(plan_ref)
    return await Merchant.count().where(
        Merchant.plan == plan.pk, Merchant.status != ResourceStatus.DELETED
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
            await PrimaryMID.update({PrimaryMID.status: status}).where(
                PrimaryMID.merchant == pk
            )
            await SecondaryMID.update({SecondaryMID.status: status}).where(
                SecondaryMID.merchant == pk
            )
            await Identifier.update({Identifier.status: status}).where(
                Identifier.merchant == pk
            )
            await Location.update({Location.status: status}).where(
                Location.merchant == pk
            )
