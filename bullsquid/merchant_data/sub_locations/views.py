"""Endpoints that operate on locations"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from bullsquid.api.auth import JWTCredentials
from bullsquid.api.errors import ResourceNotFoundError
from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.auth import AccessLevel, require_access_level
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.locations import db as locations_db
from bullsquid.merchant_data.locations.models import (
    LocationDeletionRequest,
    LocationDeletionResponse,
)
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.locations_common.models import SubLocationOverviewResponse
from bullsquid.merchant_data.sub_locations import db
from bullsquid.merchant_data.sub_locations.models import (
    SubLocationDetailMetadata,
    SubLocationDetailResponse,
    SubLocationReparentRequest,
    SubLocationReparentResponse,
)

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/locations")


@router.post(
    "/{location_ref}/sub_locations",
    response_model=SubLocationOverviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sub_location(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    location_data: SubLocationDetailMetadata,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> SubLocationOverviewResponse:
    """Create and return a response for a sub-location"""
    try:
        sub_location = await db.create_sub_location(
            location_data,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
            parent=location_ref,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return sub_location


@router.get(
    "/{location_ref}/sub_locations",
    response_model=list[SubLocationOverviewResponse],
    status_code=status.HTTP_200_OK,
)
async def list_sub_locations(
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    n: int = Query(default=10),
    p: int = Query(default=1),
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> list[SubLocationOverviewResponse]:
    """List locations on a merchant."""
    try:
        locations = await db.list_sub_locations(
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
            parent_ref=location_ref,
            n=n,
            p=p,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return locations


@router.get(
    "/{location_ref}/sub_locations/{sub_location_ref}",
    response_model=SubLocationDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_sub_location(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    sub_location_ref: UUID,
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> SubLocationDetailResponse:
    """Get sub_location details."""

    try:
        sub_location = await db.get_sub_location(
            sub_location_ref,
            merchant_ref=merchant_ref,
            plan_ref=plan_ref,
            parent_ref=location_ref,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

    return sub_location


@router.put(
    "/{location_ref}/sub_locations/{sub_location_ref}",
    response_model=SubLocationDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def edit_sub_location(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    sub_location_ref: UUID,
    fields: SubLocationDetailMetadata,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> SubLocationDetailResponse:
    """Edit a sub_locations details"""

    try:
        sub_location = await db.edit_sub_location(
            fields,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
            location_ref=sub_location_ref,
            parent_ref=location_ref,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return sub_location


@router.patch(
    "/{location_ref}/sub_locations/{sub_location_ref}",
    response_model=SubLocationReparentResponse,
    status_code=status.HTTP_200_OK,
)
async def reparent_sublocation(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    sub_location_ref: UUID,
    fields: SubLocationReparentRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> SubLocationReparentResponse:
    """Change or remove a sub-location's parent location."""

    try:
        sub_location = await db.reparent_sub_location(
            sub_location_ref,
            fields,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
            parent_ref=location_ref,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return sub_location


@router.post(
    "/{location_ref}/sub_locations/deletion",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=list[LocationDeletionResponse],
)
async def delete_sub_locations(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    deletion: LocationDeletionRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE_DELETE)
    ),
) -> list[LocationDeletionResponse]:
    """Remove a number of sub-locations from a merchant."""

    if not deletion.location_refs:
        return []

    try:
        await locations_db.confirm_locations_exist(
            deletion.location_refs,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        loc = ["body"] if ex.table == Location else ["path"]
        plural = ex.table == Location
        raise ResourceNotFoundError.from_no_such_record(
            ex, loc=loc, plural=plural
        ) from ex

    await locations_db.update_locations_status(
        deletion.location_refs,
        status=ResourceStatus.DELETED,
        plan_ref=plan_ref,
        merchant_ref=merchant_ref,
    )

    return [
        LocationDeletionResponse(
            location_ref=location_ref, location_status=ResourceStatus.DELETED
        )
        for location_ref in deletion.location_refs
    ]
