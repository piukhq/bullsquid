"""Endpoints that operate on merchants."""

from uuid import UUID

from fastapi import APIRouter, status

from bullsquid import tasks
from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, field_is_unique
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan

from . import db
from .models import (
    CreatePrimaryMIDRequest,
    PrimaryMIDDeletionListResponse,
    PrimaryMIDDeletionResponse,
    PrimaryMIDMetadata,
    PrimaryMIDResponse,
)
from .tables import PrimaryMID

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/mids")


async def create_primary_mid_response(
    primary_mid: db.PrimaryMIDResult,
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
        mid_status=primary_mid["status"],
        date_added=primary_mid["date_added"],
        txm_status=primary_mid["txm_status"],
    )


@router.get("", response_model=list[PrimaryMIDResponse])
async def list_primary_mids(
    plan_ref: UUID, merchant_ref: UUID
) -> list[PrimaryMIDResponse]:
    """List all primary MIDs for a merchant."""
    try:
        mids = await db.list_primary_mids(plan_ref=plan_ref, merchant_ref=merchant_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

    return [await create_primary_mid_response(mid) for mid in mids]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PrimaryMIDResponse)
async def create_primary_mid(
    plan_ref: UUID, merchant_ref: UUID, mid_data: CreatePrimaryMIDRequest
) -> PrimaryMIDResponse:
    """Create a primary MID for a merchant."""

    if not await field_is_unique(PrimaryMID, "mid", mid_data.mid_metadata.mid):
        raise UniqueError(loc=["body", "mid_metadata", "mid"])

    try:
        mid = await db.create_primary_mid(
            mid_data.mid_metadata, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        loc = ["path"] if ex.table in [Plan, Merchant] else ["body", "mid_metadata"]
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc)

    if mid_data.onboard:
        await tasks.queue.push(tasks.OnboardPrimaryMIDs(mid_refs=[mid["pk"]]))

    return await create_primary_mid_response(mid)


@router.post(
    "/deletion",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PrimaryMIDDeletionListResponse,
)
async def delete_primary_mids(
    plan_ref: UUID, merchant_ref: UUID, mid_refs: list[UUID]
) -> PrimaryMIDDeletionListResponse:
    """Remove a number of primary MIDs from a merchant."""

    if not mid_refs:
        return PrimaryMIDDeletionListResponse(mids=[])

    try:
        onboarded, not_onboarded = await db.filter_onboarded_mid_refs(
            mid_refs, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        loc = ["body"] if ex.table == PrimaryMID else ["path"]
        plural = ex.table == PrimaryMID
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc, plural=plural)

    if onboarded:
        await db.update_primary_mids_status(
            onboarded,
            status=ResourceStatus.PENDING_DELETION,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
        await tasks.queue.push(tasks.OffboardAndDeletePrimaryMIDs(mid_refs=onboarded))

    if not_onboarded:
        await db.update_primary_mids_status(
            not_onboarded,
            status=ResourceStatus.DELETED,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )

    return PrimaryMIDDeletionListResponse(
        mids=[
            PrimaryMIDDeletionResponse(
                mid_ref=mid_ref, mid_status=ResourceStatus.PENDING_DELETION
            )
            for mid_ref in onboarded
        ]
        + [
            PrimaryMIDDeletionResponse(
                mid_ref=mid_ref, mid_status=ResourceStatus.DELETED
            )
            for mid_ref in not_onboarded
        ]
    )
