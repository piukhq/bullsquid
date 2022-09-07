"""Endpoints that operate on merchants."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from bullsquid import tasks
from bullsquid.api.errors import DataError, ResourceNotFoundError, UniqueError
from bullsquid.db import InvalidData, NoSuchRecord, field_is_unique
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.locations.db import get_location_instance
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan

from . import db
from .models import (
    CreatePrimaryMIDRequest,
    LocationLinkRequest,
    LocationLinkResponse,
    PrimaryMIDDeletionRequest,
    PrimaryMIDDeletionResponse,
    PrimaryMIDMetadata,
    PrimaryMIDResponse,
    UpdatePrimaryMIDRequest,
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
    plan_ref: UUID,
    merchant_ref: UUID,
    n: int = Query(default=10),
    p: int = Query(default=1),
) -> list[PrimaryMIDResponse]:
    """List all primary MIDs for a merchant."""
    try:
        mids = await db.list_primary_mids(
            plan_ref=plan_ref, merchant_ref=merchant_ref, n=n, p=p
        )
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
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc) from ex
    except InvalidData as ex:
        raise DataError.from_invalid_data(
            ex, loc=["body", "mid_metadata", "visa_bin"]
        ) from ex

    if mid_data.onboard:
        await tasks.queue.push(tasks.OnboardPrimaryMIDs(mid_refs=[mid["pk"]]))

    return await create_primary_mid_response(mid)


@router.patch("/{mid_ref}", response_model=PrimaryMIDResponse)
async def update_primary_mid(
    plan_ref: UUID,
    merchant_ref: UUID,
    mid_ref: UUID,
    mid_data: UpdatePrimaryMIDRequest,
) -> PrimaryMIDResponse:
    """Update a primary MID's editable fields."""
    try:
        mid = await db.update_primary_mid(
            mid_ref, mid_data, merchant_ref=merchant_ref, plan_ref=plan_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex
    except InvalidData as ex:
        raise DataError.from_invalid_data(ex, loc=["body", "visa_bin"]) from ex

    return await create_primary_mid_response(mid)


@router.post(
    "/deletion",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=list[PrimaryMIDDeletionResponse],
)
async def delete_primary_mids(
    plan_ref: UUID, merchant_ref: UUID, deletion: PrimaryMIDDeletionRequest
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
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc)

    primary_mid.location = location
    await primary_mid.save()

    return LocationLinkResponse(
        location_ref=location.pk,
        location_title=location.title,
    )


@router.delete("/{mid_ref}/location_link")
async def delete_primary_mid_location_link(
    plan_ref: UUID, merchant_ref: UUID, mid_ref: UUID
) -> None:
    """Delete the link between a location and a primary MID."""
    try:
        primary_mid = await db.get_primary_mid_instance(
            mid_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

    primary_mid.location = None
    await primary_mid.save()
