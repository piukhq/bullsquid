"""Database operations for secondary MIDs."""
from datetime import datetime
from typing import TypedDict
from uuid import UUID

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.payment_schemes.db import get_payment_scheme_by_code
from bullsquid.merchant_data.secondary_mids.models import SecondaryMIDMetadata

from .tables import SecondaryMID

SecondaryMIDResult = TypedDict(
    "SecondaryMIDResult",
    {
        "pk": UUID,
        "payment_scheme.code": int,
        "secondary_mid": str,
        "payment_scheme_store_name": str,
        "payment_enrolment_status": str,
        "date_added": datetime,
        "txm_status": str,
        "status": str,
    },
)


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


async def create_secondary_mid(
    secondary_mid_data: SecondaryMIDMetadata,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> SecondaryMIDResult:
    """Create a secondary MID for the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    payment_scheme = await get_payment_scheme_by_code(
        secondary_mid_data.payment_scheme_code
    )
    secondary_mid = SecondaryMID(
        secondary_mid=secondary_mid_data.secondary_mid,
        payment_scheme_store_name=secondary_mid_data.payment_scheme_store_name,
        payment_scheme=payment_scheme,
        payment_enrolment_status=secondary_mid_data.payment_enrolment_status,
        merchant=merchant,
    )
    await secondary_mid.save()

    return {
        "pk": secondary_mid.pk,
        "payment_scheme.code": payment_scheme.code,
        "secondary_mid": secondary_mid.secondary_mid,
        "payment_scheme_store_name": secondary_mid.payment_scheme_store_name,
        "payment_enrolment_status": secondary_mid.payment_enrolment_status,
        "date_added": secondary_mid.date_added,
        "txm_status": secondary_mid.txm_status,
        "status": secondary_mid.status,
    }


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
