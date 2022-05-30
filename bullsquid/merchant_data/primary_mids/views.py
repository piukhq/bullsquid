"""Endpoints that operate on merchants."""

from uuid import UUID

from fastapi import APIRouter, status

from bullsquid import tasks
from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.merchant_data.db import NoSuchRecord, field_is_unique
from bullsquid.merchant_data.enums import ResourceStatus

from .db import (
    PrimaryMIDResult,
    create_primary_mid,
    filter_onboarded_mid_refs,
    list_primary_mids,
    update_primary_mids_status,
)
from .models import (
    CreatePrimaryMIDRequest,
    PrimaryMIDDeletionListResponse,
    PrimaryMIDDeletionResponse,
    PrimaryMIDListResponse,
    PrimaryMIDMetadata,
    PrimaryMIDResponse,
)
from .tables import PrimaryMID

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/mids")


async def create_primary_mid_response(
    primary_mid: PrimaryMIDResult,
) -> PrimaryMIDResponse:
    """Creates a PrimaryMIDResponse instance from the given primary MID."""
    return PrimaryMIDResponse(
        mid_ref=primary_mid["pk"],
        mid_metadata=PrimaryMIDMetadata(
            payment_scheme_code=primary_mid["payment_scheme.code"],
            mid=primary_mid["mid"],
            visa_bin=primary_mid["visa_bin"],
            payment_enrolment_status=primary_mid["payment_enrolment_status"],
        ),
        date_added=primary_mid["date_added"],
        txm_status=primary_mid["txm_status"],
    )


async def create_primary_mid_list_response(
    primary_mids: list[PrimaryMIDResult],
) -> PrimaryMIDListResponse:
    """Creates a PrimaryMIDListResponse instance from the given primary MIDs."""
    return PrimaryMIDListResponse(
        mids=[await create_primary_mid_response(mid) for mid in primary_mids]
    )


@router.get("", response_model=PrimaryMIDListResponse)
async def _(plan_ref: UUID, merchant_ref: UUID) -> PrimaryMIDListResponse:
    """List all primary MIDs for a merchant."""
    try:
        mids = await list_primary_mids(plan_ref=plan_ref, merchant_ref=merchant_ref)
    except NoSuchRecord as ex:
        # the combination of plan & merchant refs did not lead to a merchant.
        raise ResourceNotFoundError(
            loc=["path", "merchant_ref"], resource_name="Merchant"
        ) from ex

    return await create_primary_mid_list_response(mids)


@router.post("", response_model=PrimaryMIDResponse)
async def _(
    plan_ref: UUID, merchant_ref: UUID, mid_data: CreatePrimaryMIDRequest
) -> PrimaryMIDResponse:
    """Create a primary MID for a merchant."""

    if not await field_is_unique(PrimaryMID, "mid", mid_data.mid_metadata.mid):
        raise UniqueError(loc=["body", "mid_metadata", "mid"])

    try:
        mid = await create_primary_mid(
            mid_data.mid_metadata, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        # the combination of plan & merchant refs did not lead to a merchant.
        raise ResourceNotFoundError(
            loc=["path", "merchant_ref"], resource_name="Merchant"
        ) from ex

    if mid_data.onboard:
        await tasks.queue.push(tasks.OnboardPrimaryMIDs(mid_refs=[mid["pk"]]))

    return await create_primary_mid_response(mid)


@router.post("/deletion", status_code=status.HTTP_202_ACCEPTED)
async def _(
    plan_ref: UUID, merchant_ref: UUID, mid_refs: list[UUID]
) -> PrimaryMIDDeletionListResponse:
    """Remove a number of primary MIDs from a merchant."""

    onboarded, not_onboarded = await filter_onboarded_mid_refs(
        mid_refs, plan_ref=plan_ref, merchant_ref=merchant_ref
    )
    if onboarded:
        await update_primary_mids_status(
            onboarded,
            status=ResourceStatus.PENDING_DELETION,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
        await tasks.queue.push(tasks.OffboardAndDeletePrimaryMIDs(mid_refs=onboarded))

    if not_onboarded:
        await update_primary_mids_status(
            not_onboarded,
            status=ResourceStatus.DELETED,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )

    return PrimaryMIDDeletionListResponse(
        mids=[
            PrimaryMIDDeletionResponse(
                mid_ref=mid_ref, status=ResourceStatus.PENDING_DELETION
            )
            for mid_ref in onboarded
        ]
        + [
            PrimaryMIDDeletionResponse(mid_ref=mid_ref, status=ResourceStatus.DELETED)
            for mid_ref in not_onboarded
        ]
    )
