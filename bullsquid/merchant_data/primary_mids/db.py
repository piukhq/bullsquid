"""Database access layer for primary MID operations."""

from typing import Any
from uuid import UUID

from piccolo.columns import Column

from bullsquid.db import InvalidData, NoSuchRecord, paginate
from bullsquid.merchant_data.enums import (
    PaymentEnrolmentStatus,
    ResourceStatus,
    TXMStatus,
)
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.payment_schemes.db import get_payment_scheme
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.primary_mids.models import (
    LocationLinkResponse,
    PrimaryMIDDetailResponse,
    PrimaryMIDMetadata,
    PrimaryMIDOverviewResponse,
    UpdatePrimaryMIDRequest,
)
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID


def detail_response(mid: PrimaryMID) -> PrimaryMIDDetailResponse:
    if isinstance(mid.payment_scheme, (str, UUID)):
        raise ValueError("PrimaryMID.payment_scheme must be loaded for detail response")
    if isinstance(mid.location, (str, UUID)):
        raise ValueError("PrimaryMID.location must be loaded for detail response")

    return PrimaryMIDDetailResponse(
        mid=PrimaryMIDOverviewResponse(
            mid_ref=mid.pk,
            mid_metadata=PrimaryMIDMetadata(
                payment_scheme_slug=mid.payment_scheme.slug,
                mid=mid.mid,
                visa_bin=mid.visa_bin,
                payment_enrolment_status=mid.payment_enrolment_status,
            ),
            mid_status=mid.status,
            date_added=mid.date_added,
            txm_status=mid.txm_status,
        ),
        location=LocationLinkResponse(
            location_ref=mid.location.pk,
            location_title=mid.location.display_text,
        )
        if mid.location and mid.location.pk
        else None,
    )


def overview_response(mid: PrimaryMID) -> PrimaryMIDOverviewResponse:
    if isinstance(mid.payment_scheme, (str, UUID)):
        raise ValueError(
            "PrimaryMID.payment_scheme must be loaded for overview response"
        )

    return PrimaryMIDOverviewResponse(
        mid_ref=mid.pk,
        mid_metadata=PrimaryMIDMetadata(
            payment_scheme_slug=mid.payment_scheme.slug,
            mid=mid.mid,
            visa_bin=mid.visa_bin,
            payment_enrolment_status=mid.payment_enrolment_status,
        ),
        mid_status=mid.status,
        date_added=mid.date_added,
        txm_status=mid.txm_status,
    )


async def get_primary_mid_instance(
    pk: UUID,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> PrimaryMID:
    """Get a primary MID instance by primary key."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    mid = await PrimaryMID.objects(PrimaryMID.payment_scheme, PrimaryMID.location).get(
        (PrimaryMID.pk == pk) & (PrimaryMID.merchant == merchant)
    )

    if not mid:
        raise NoSuchRecord(PrimaryMID)

    return mid


async def get_primary_mid(
    pk: UUID,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> PrimaryMIDDetailResponse:
    """Get primary MID details by its primary key."""
    mid = await get_primary_mid_instance(
        pk, plan_ref=plan_ref, merchant_ref=merchant_ref
    )

    return detail_response(mid)


async def get_primary_mids(
    pks: set[UUID],
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> list[PrimaryMIDOverviewResponse]:
    """Get a number of primary MIDs by their primary keys."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    mids = await PrimaryMID.objects(PrimaryMID.payment_scheme).where(
        PrimaryMID.pk.is_in(list(pks)),
        PrimaryMID.merchant == merchant,
    )

    if len(mids) != len(pks):
        raise NoSuchRecord(PrimaryMID)

    return [overview_response(mid) for mid in mids]


async def list_primary_mids(
    *, plan_ref: UUID, merchant_ref: UUID, n: int, p: int
) -> list[PrimaryMIDOverviewResponse]:
    """Return a list of all primary MIDs on the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    results = await paginate(
        PrimaryMID.objects(PrimaryMID.payment_scheme).where(
            PrimaryMID.merchant == merchant,
        ),
        n=n,
        p=p,
    )

    return [overview_response(result) for result in results]


async def filter_onboarded_mid_refs(
    mid_refs: set[UUID], *, plan_ref: UUID, merchant_ref: UUID
) -> tuple[set[UUID], set[UUID]]:
    """
    Split the given list of primary MID refs into onboarded and not.
    """
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    q_mid_refs = list(mid_refs)

    count = await PrimaryMID.count().where(PrimaryMID.pk.is_in(q_mid_refs))
    if count != len(mid_refs):
        raise NoSuchRecord(PrimaryMID)

    return {
        result["pk"]
        for result in await PrimaryMID.select(PrimaryMID.pk).where(
            PrimaryMID.pk.is_in(q_mid_refs),
            PrimaryMID.merchant == merchant,
            PrimaryMID.txm_status == TXMStatus.ONBOARDED,
        )
    }, {
        result["pk"]
        for result in await PrimaryMID.select(PrimaryMID.pk).where(
            PrimaryMID.pk.is_in(q_mid_refs),
            PrimaryMID.merchant == merchant,
            PrimaryMID.txm_status != TXMStatus.ONBOARDED,
        )
    }


async def create_primary_mid(
    mid_data: PrimaryMIDMetadata,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> PrimaryMIDOverviewResponse:
    """Create a primary MID for the given merchant."""

    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    payment_scheme = await get_payment_scheme(mid_data.payment_scheme_slug)
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

    return overview_response(mid)


async def update_primary_mid(
    pk: UUID, fields: UpdatePrimaryMIDRequest, *, plan_ref: UUID, merchant_ref: UUID
) -> PrimaryMIDOverviewResponse:
    """Update a primary MID's editable fields."""
    mid = await get_primary_mid_instance(
        pk, plan_ref=plan_ref, merchant_ref=merchant_ref
    )

    if fields.visa_bin and mid.payment_scheme.slug != "visa":
        raise InvalidData(PaymentScheme)

    for name, value in fields.dict(exclude_unset=True).items():
        setattr(mid, name, value)
    await mid.save()

    return overview_response(mid)


async def update_primary_mids_status(
    mid_refs: set[UUID],
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
        PrimaryMID.pk.is_in(list(mid_refs)), PrimaryMID.merchant == merchant
    )


async def bulk_update_primary_mids(
    mid_refs: set[UUID],
    status: PaymentEnrolmentStatus,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> list[PrimaryMIDOverviewResponse]:
    """Update a primary MID's editable fields."""
    await get_primary_mids(mid_refs, plan_ref=plan_ref, merchant_ref=merchant_ref)

    await PrimaryMID.update({PrimaryMID.payment_enrolment_status: status}).where(
        PrimaryMID.pk.is_in(list(mid_refs))
    )
    mids = await get_primary_mids(
        mid_refs, plan_ref=plan_ref, merchant_ref=merchant_ref
    )
    return mids
