"""Endpoints that operate on merchants."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from bullsquid.api.auth import AccessLevel, JWTCredentials
from bullsquid.api.errors import DataError, ResourceNotFoundError, UniqueError
from bullsquid.db import InvalidData, NoSuchRecord, fields_are_unique
from bullsquid.merchant_data import tasks
from bullsquid.merchant_data.auth import require_access_level
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.locations.db import get_location_instance
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids import db
from bullsquid.merchant_data.primary_mids.models import (
    CreatePrimaryMIDRequest,
    LocationLinkRequest,
    LocationLinkResponse,
    PrimaryMIDDeletionRequest,
    PrimaryMIDDeletionResponse,
    PrimaryMIDDetailResponse,
    PrimaryMIDOverviewResponse,
    UpdatePrimaryMIDRequest,
)
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.settings import settings

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/mids")


@router.get("", response_model=list[PrimaryMIDOverviewResponse])
async def list_primary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    n: int = Query(default=settings.default_page_size),
    p: int = Query(default=1),
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> list[PrimaryMIDOverviewResponse]:
    """List all primary MIDs for a merchant."""
    try:
        mids = await db.list_primary_mids(
            plan_ref=plan_ref, merchant_ref=merchant_ref, n=n, p=p
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return mids


@router.get("/{mid_ref}", response_model=PrimaryMIDDetailResponse)
async def get_primary_mid_details(
    plan_ref: UUID,
    merchant_ref: UUID,
    mid_ref: UUID,
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> PrimaryMIDDetailResponse:
    """Get the details of a single primary MID on a merchant."""
    try:
        mid = await db.get_primary_mid(
            mid_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return mid


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=PrimaryMIDOverviewResponse
)
async def create_primary_mid(
    plan_ref: UUID,
    merchant_ref: UUID,
    mid_data: CreatePrimaryMIDRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> PrimaryMIDOverviewResponse:
    """Create a primary MID for a merchant."""

    if not await fields_are_unique(
        PrimaryMID,
        {
            PrimaryMID.mid: mid_data.mid_metadata.mid,
            PrimaryMID.payment_scheme: mid_data.mid_metadata.payment_scheme_slug,
            PrimaryMID.merchant.plan: plan_ref,
        },
    ):
        raise UniqueError(loc=["body", "mid_metadata", "mid"])

    try:
        mid = await db.create_primary_mid(
            mid_data.mid_metadata, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        loc = ["path"] if ex.table in (Plan, Merchant) else ["body", "mid_metadata"]
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc) from ex
    except InvalidData as ex:
        raise DataError.from_invalid_data(
            ex, loc=["body", "mid_metadata", "visa_bin"]
        ) from ex

    if mid_data.onboard:
        await tasks.queue.push(tasks.OnboardPrimaryMIDs(mid_refs=[mid.mid_ref]))

    return mid


@router.patch("/{mid_ref}", response_model=PrimaryMIDOverviewResponse)
async def update_primary_mid(
    plan_ref: UUID,
    merchant_ref: UUID,
    mid_ref: UUID,
    mid_data: UpdatePrimaryMIDRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> PrimaryMIDOverviewResponse:
    """Update a primary MID's editable fields."""
    try:
        mid = await db.update_primary_mid(
            mid_ref, mid_data, merchant_ref=merchant_ref, plan_ref=plan_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex
    except InvalidData as ex:
        raise DataError.from_invalid_data(ex, loc=["body", "visa_bin"]) from ex

    return mid


@router.post(
    "/deletion",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=list[PrimaryMIDDeletionResponse],
)
async def delete_primary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    deletion: PrimaryMIDDeletionRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE_DELETE)
    ),
) -> list[PrimaryMIDDeletionResponse]:
    """Remove a number of primary MIDs from a merchant."""

    if not deletion.mid_refs:
        return []

    try:
        onboarded, not_onboarded = await db.filter_onboarded_mid_refs(
            deletion.mid_refs, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        loc = ["body"] if ex.table == PrimaryMID else ["path"]
        plural = ex.table == PrimaryMID
        raise ResourceNotFoundError.from_no_such_record(
            ex, loc=loc, plural=plural
        ) from ex

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

    return [
        PrimaryMIDDeletionResponse(
            mid_ref=mid_ref, mid_status=ResourceStatus.PENDING_DELETION
        )
        for mid_ref in onboarded
    ] + [
        PrimaryMIDDeletionResponse(mid_ref=mid_ref, mid_status=ResourceStatus.DELETED)
        for mid_ref in not_onboarded
    ]


@router.put(
    "/{mid_ref}/location_link",
    response_model=LocationLinkResponse,
)
async def link_primary_mid_to_location(
    plan_ref: UUID,
    merchant_ref: UUID,
    mid_ref: UUID,
    link_request: LocationLinkRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> LocationLinkResponse:
    """Link a location to a primary MID."""
    try:
        primary_mid = await db.get_primary_mid_instance(
            mid_ref,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
        location = await get_location_instance(
            link_request.location_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        loc = ["body"] if ex.table == Location else ["path"]
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc) from ex

    primary_mid.location = location
    await primary_mid.save()

    return LocationLinkResponse(
        location_ref=location.pk,
        location_title=location.display_text,
    )


@router.delete("/{mid_ref}/location_link", status_code=status.HTTP_204_NO_CONTENT)
async def delete_primary_mid_location_link(
    plan_ref: UUID,
    merchant_ref: UUID,
    mid_ref: UUID,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> None:
    """Delete the link between a location and a primary MID."""
    try:
        primary_mid = await db.get_primary_mid_instance(
            mid_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    primary_mid.location = None
    await primary_mid.save()
