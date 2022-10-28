"""Database access layer for primary MID operations."""

from datetime import datetime
from typing import Any, TypedDict
from uuid import UUID

from piccolo.columns import Column

from bullsquid.db import InvalidData, NoSuchRecord, paginate
from bullsquid.merchant_data.enums import (
    PaymentEnrolmentStatus,
    ResourceStatus,
    TXMStatus,
)
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.payment_schemes.db import get_payment_scheme_by_code
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.primary_mids.models import (
    PrimaryMIDMetadata,
    UpdatePrimaryMIDRequest,
)
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID

PrimaryMIDResult = TypedDict(
    "PrimaryMIDResult",
    {
        "pk": UUID,
        "payment_scheme.code": int,
        "mid": str,
        "visa_bin": str,
        "payment_enrolment_status": PaymentEnrolmentStatus,
        "status": ResourceStatus,
        "date_added": datetime,
        "txm_status": TXMStatus,
    },
)


async def get_primary_mid_instance(
    pk: UUID,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> PrimaryMID:
    """Get a primary MID instance by primary key."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    mid = await PrimaryMID.objects(PrimaryMID.payment_scheme).get(
        (PrimaryMID.pk == pk) & (PrimaryMID.merchant == merchant)
    )

    if not mid:
        raise NoSuchRecord(PrimaryMID)

    return mid


async def list_primary_mids(
    *, plan_ref: UUID, merchant_ref: UUID, n: int, p: int
) -> list[PrimaryMIDResult]:
    """Return a list of all primary MIDs on the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    return await paginate(
        PrimaryMID.select(
            PrimaryMID.pk,
            PrimaryMID.payment_scheme.code,
            PrimaryMID.mid,
            PrimaryMID.visa_bin,
            PrimaryMID.payment_enrolment_status,
            PrimaryMID.status,
            PrimaryMID.date_added,
            PrimaryMID.txm_status,
        ).where(
            PrimaryMID.merchant == merchant,
        ),
        n=n,
        p=p,
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
        raise NoSuchRecord(PrimaryMID)

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

    if mid_data.visa_bin and payment_scheme.slug != "visa":
        raise InvalidData(PaymentScheme)

    await mid.save()

    return {
        "pk": mid.pk,
        "payment_scheme.code": payment_scheme.code,
        "mid": mid.mid,
        "visa_bin": mid.visa_bin,
        "payment_enrolment_status": PaymentEnrolmentStatus(
            mid.payment_enrolment_status
        ),
        "status": ResourceStatus(mid.status),
        "date_added": mid.date_added,
        "txm_status": TXMStatus(mid.txm_status),
    }


async def update_primary_mid(
    pk: UUID, fields: UpdatePrimaryMIDRequest, *, plan_ref: UUID, merchant_ref: UUID
) -> PrimaryMIDResult:
    """Update a primary MID's editable fields."""
    mid = await get_primary_mid_instance(
        pk, plan_ref=plan_ref, merchant_ref=merchant_ref
    )

    if fields.visa_bin and mid.payment_scheme.slug != "visa":
        raise InvalidData(PaymentScheme)

    for name, value in fields.dict(exclude_unset=True).items():
        setattr(mid, name, value)
    await mid.save()

    return {
        "pk": mid.pk,
        "payment_scheme.code": mid.payment_scheme.code,
        "mid": mid.mid,
        "visa_bin": mid.visa_bin,
        "payment_enrolment_status": PaymentEnrolmentStatus(
            mid.payment_enrolment_status
        ),
        "status": ResourceStatus(mid.status),
        "date_added": mid.date_added,
        "txm_status": TXMStatus(mid.txm_status),
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
    values: dict[Column | str, Any] = {PrimaryMID.status: status}

    if status == ResourceStatus.DELETED:
        values[PrimaryMID.location] = None

    await PrimaryMID.update(values).where(
        PrimaryMID.pk.is_in(mid_refs), PrimaryMID.merchant == merchant
    )
