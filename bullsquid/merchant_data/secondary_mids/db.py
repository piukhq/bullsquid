"""Database operations for secondary MIDs."""
from uuid import UUID

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.merchants.db import get_merchant

from .tables import SecondaryMID


async def get_secondary_mid(pk: UUID) -> SecondaryMID:
    """Returns a secondary MID."""
    secondary_mid = await SecondaryMID.objects().get(SecondaryMID.pk == pk)
    if not secondary_mid:
        raise NoSuchRecord

    return secondary_mid


async def filter_onboarded_secondary_mids(
    secondary_mid_refs: list[UUID], *, plan_ref: UUID, merchant_ref: UUID
) -> tuple[list[UUID], list[UUID]]:
    """
    Split the given list of secondary MID refs into onboarded and not onboarded/offboarded.
    """
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    # remove duplicates to ensure count mismatches are not caused by duplicate secondary MIDs
    secondary_mid_refs = list(set(secondary_mid_refs))

    count = await SecondaryMID.count().where(SecondaryMID.pk.is_in(secondary_mid_refs))
    if count != len(secondary_mid_refs):
        raise NoSuchRecord

    return [
        result["pk"]
        for result in await SecondaryMID.select(SecondaryMID.pk).where(
            SecondaryMID.pk.is_in(secondary_mid_refs),
            SecondaryMID.merchant == merchant,
            SecondaryMID.txm_status == TXMStatus.ONBOARDED,
        )
    ], [
        result["pk"]
        for result in await SecondaryMID.select(SecondaryMID.pk).where(
            SecondaryMID.pk.is_in(secondary_mid_refs),
            SecondaryMID.merchant == merchant,
            SecondaryMID.txm_status != TXMStatus.ONBOARDED,
        )
    ]


async def update_secondary_mids_status(
    secondary_mid_refs: list[UUID],
    *,
    status: ResourceStatus,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> None:
    """Updates the status for a list of secondary MIDs on a merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    await SecondaryMID.update({SecondaryMID.status: status}).where(
        SecondaryMID.pk.is_in(secondary_mid_refs), SecondaryMID.merchant == merchant
    )
