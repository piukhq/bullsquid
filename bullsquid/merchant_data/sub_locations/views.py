"""Endpoints that operate on locations"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from bullsquid.api.auth import JWTCredentials
from bullsquid.api.errors import ResourceNotFoundError
from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.auth import AccessLevel, require_access_level
from bullsquid.merchant_data.locations_common.models import SubLocationOverviewResponse
from bullsquid.merchant_data.sub_locations import db
from bullsquid.merchant_data.sub_locations.models import (
    SubLocationDetailMetadata,
    SubLocationDetailResponse,
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
