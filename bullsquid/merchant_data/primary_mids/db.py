"""Database access layer for primary MID operations."""

from datetime import datetime
from typing import TypedDict
from uuid import UUID

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.payment_schemes.db import get_payment_scheme_by_code
from bullsquid.merchant_data.primary_mids.models import PrimaryMIDMetadata

from .tables import PrimaryMID

PrimaryMIDResult = TypedDict(
    "PrimaryMIDResult",
    {
        "pk": UUID,
        "payment_scheme.code": int,
        "mid": str,
        "visa_bin": str,
        "payment_enrolment_status": str,
        "date_added": datetime,
        "txm_status": str,
    },
)


async def list_primary_mids(
    *, plan_ref: UUID, merchant_ref: UUID
) -> list[PrimaryMIDResult]:
    """Return a list of all primary MIDs on the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    return await PrimaryMID.select(
        PrimaryMID.pk,
        PrimaryMID.payment_scheme.code,
        PrimaryMID.mid,
        PrimaryMID.visa_bin,
        PrimaryMID.payment_enrolment_status,
        PrimaryMID.date_added,
        PrimaryMID.txm_status,
    ).where(
        PrimaryMID.merchant == merchant,
        PrimaryMID.status != ResourceStatus.DELETED,
    )


async def filter_onboarded_mid_refs(
    mid_refs: list[UUID], *, plan_ref: UUID, merchant_ref: UUID
) -> tuple[list[UUID], list[UUID]]:
    """
    Split the given list of primary MID refs into onboarded and not onboarded/offboarded.
    """
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    # remove duplicates to ensure count mismatches are not caused by duplicate MIDs
    mid_refs = list(set(mid_refs))

    count = await PrimaryMID.count().where(PrimaryMID.pk.is_in(mid_refs))
    if count != len(mid_refs):
        raise NoSuchRecord

    return [
        result["pk"]
        for result in await PrimaryMID.select(PrimaryMID.pk).where(
            PrimaryMID.pk.is_in(mid_refs),
            PrimaryMID.merchant == merchant,
            PrimaryMID.txm_status == TXMStatus.ONBOARDED,
        )
    ], [
        result["pk"]
        for result in await PrimaryMID.select(PrimaryMID.pk).where(
            PrimaryMID.pk.is_in(mid_refs),
            PrimaryMID.merchant == merchant,
            PrimaryMID.txm_status != TXMStatus.ONBOARDED,
        )
    ]


async def create_primary_mid(
    mid_data: PrimaryMIDMetadata,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> PrimaryMIDResult:
    """Create a primary MID for the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    payment_scheme = await get_payment_scheme_by_code(mid_data.payment_scheme_code)
    mid = PrimaryMID(
        mid=mid_data.mid,
        visa_bin=mid_data.visa_bin,
        payment_scheme=payment_scheme,
        payment_enrolment_status=mid_data.payment_enrolment_status,
        merchant=merchant,
    )
    await mid.save()

    return {
        "pk": mid.pk,
        "payment_scheme.code": payment_scheme.code,
        "mid": mid.mid,
        "visa_bin": mid.visa_bin,
        "payment_enrolment_status": mid.payment_enrolment_status,
        "date_added": mid.date_added,
        "txm_status": mid.txm_status,
    }


async def update_primary_mids_status(
    mid_refs: list[UUID],
    *,
    status: ResourceStatus,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> None:
    """Updates the status for a list of primary MIDs on a merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    await PrimaryMID.update({PrimaryMID.status: status}).where(
        PrimaryMID.pk.is_in(mid_refs), PrimaryMID.merchant == merchant
    )
