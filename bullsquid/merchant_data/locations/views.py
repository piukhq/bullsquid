"""Endpoints that operate on locations"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from bullsquid.api.auth import JWTCredentials
from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, field_is_unique
from bullsquid.merchant_data.auth import AccessLevel, require_access_level
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.locations import db
from bullsquid.merchant_data.locations.models import (
    AvailablePrimaryMID,
    LocationDeletionRequest,
    LocationDeletionResponse,
    LocationDetailMetadata,
    LocationDetailResponse,
    LocationOverviewResponse,
    PrimaryMIDLinkRequest,
    PrimaryMIDLinkResponse,
    SecondaryMIDLinkRequest,
    SecondaryMIDLinkResponse,
)
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.primary_mids.models import LocationLinkResponse
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mid_location_links.db import (
    create_location_primary_mid_links,
    create_secondary_mid_location_links,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/locations")


@router.get("", response_model=list[LocationOverviewResponse])
async def list_locations(  # pylint: disable=too-many-arguments
    plan_ref: UUID,
    merchant_ref: UUID,
    exclude_secondary_mid: UUID | None = Query(default=None),
    include_sub_locations: bool = Query(default=False),
    n: int = Query(default=10),
    p: int = Query(default=1),
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> list[LocationOverviewResponse]:
    """List locations on a merchant."""
    try:
        locations = await db.list_locations(
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
            exclude_secondary_mid=exclude_secondary_mid,
            include_sub_locations=include_sub_locations,
            n=n,
            p=p,
        )
    except NoSuchRecord as ex:
        loc = ["query"] if ex.table == SecondaryMID else ["path"]
        override_field_name = (
            "exclude_secondary_mid" if ex.table == SecondaryMID else None
        )
        raise ResourceNotFoundError.from_no_such_record(
            ex, loc=loc, override_field_name=override_field_name
        ) from ex

    return locations


@router.get("/{location_ref}", response_model=LocationDetailResponse)
async def get_location(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> LocationDetailResponse:
    """Get location details."""
    try:
        location = await db.get_location(
            location_ref, merchant_ref=merchant_ref, plan_ref=plan_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex
    return location


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=LocationOverviewResponse,
)
async def create_location(
    location_data: LocationDetailMetadata,
    plan_ref: UUID,
    merchant_ref: UUID,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> LocationOverviewResponse:
    """Create a location for the given merchant."""
    if not await field_is_unique(Location, "location_id", location_data.location_id):
        raise UniqueError(loc=["body", "location_id"])

    try:
        location = await db.create_location(
            location_data,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return location


@router.post(
    "/deletion",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=list[LocationDeletionResponse],
)
async def delete_locations(
    plan_ref: UUID,
    merchant_ref: UUID,
    deletion: LocationDeletionRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE_DELETE)
    ),
) -> list[LocationDeletionResponse]:
    """Remove a number of locations from a merchant."""

    if not deletion.location_refs:
        return []

    try:
        await db.confirm_locations_exist(
            deletion.location_refs, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        loc = ["body"] if ex.table == Location else ["path"]
        plural = ex.table == Location
        raise ResourceNotFoundError.from_no_such_record(
            ex, loc=loc, plural=plural
        ) from ex

    await db.update_locations_status(
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


@router.post(
    "/{location_ref}/mids",
    response_model=list[PrimaryMIDLinkResponse],
)
async def link_location_to_primary_mid(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    link_request: PrimaryMIDLinkRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> list[PrimaryMIDLinkResponse]:
    """
    Link a primary MID to a location.
    """
    try:
        mids = await create_location_primary_mid_links(
            location_ref=location_ref,
            primary_mid_refs=link_request.mid_refs,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        loc = ["body"] if ex.table == PrimaryMID else ["path"]
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc) from ex

    return [
        PrimaryMIDLinkResponse(
            mid_ref=mid.pk,
            payment_scheme_slug=mid.payment_scheme,
            mid_value=mid.mid,
        )
        for mid in mids
    ]


@router.post(
    "/{location_ref}/secondary_mid_location_links",
    responses={
        status.HTTP_200_OK: {"model": list[SecondaryMIDLinkResponse]},
        status.HTTP_201_CREATED: {"model": list[SecondaryMIDLinkResponse]},
    },
)
async def link_location_to_secondary_mid(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    link_request: SecondaryMIDLinkRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> JSONResponse:
    """
    Link a secondary MID to a location.
    """
    try:
        links, created = await create_secondary_mid_location_links(
            refs=[
                (secondary_mid_ref, location_ref)
                for secondary_mid_ref in link_request.secondary_mid_refs
            ],
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        loc = ["body"] if ex.table == SecondaryMID else ["path"]
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc) from ex

    content = jsonable_encoder(
        [
            SecondaryMIDLinkResponse(
                link_ref=link.pk,
                secondary_mid_ref=link.secondary_mid.pk,
                payment_scheme_slug=link.secondary_mid.payment_scheme,
                secondary_mid_value=link.secondary_mid.secondary_mid,
            )
            for link in links
        ]
    )
    return JSONResponse(
        content=content,
        status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@router.get("/{location_ref}/available_mids", response_model=list[AvailablePrimaryMID])
async def list_available_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> list[AvailablePrimaryMID]:
    """returns the list of MIDs that are available for association with a location"""
    try:
        available_mids = await db.list_available_primary_mids(
            plan_ref, merchant_ref=merchant_ref, location_ref=location_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex
    return [
        AvailablePrimaryMID(
            location_link=LocationLinkResponse(
                location_ref=mid["location.pk"],
                location_title=Location(
                    name=mid["location.name"],
                    address_line_1=mid["location.address_line_1"],
                    town_city=mid["location.town_city"],
                    postcode=mid["location.postcode"],
                ).display_text,
            )
            if mid["location.pk"]
            else None,
            mid=PrimaryMIDLinkResponse(
                mid_ref=mid["pk"],
                payment_scheme_slug=mid["payment_scheme.slug"],
                mid_value=mid["mid"],
            ),
        )
        for mid in available_mids
    ]


@router.get("/{location_ref}/mids", response_model=list[PrimaryMIDLinkResponse])
async def list_location_primary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    n: int = Query(default=10),
    p: int = Query(default=1),
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> list[PrimaryMIDLinkResponse]:
    """List MIDs associated with location."""
    try:
        mids = await db.list_associated_primary_mids(
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
            location_ref=location_ref,
            n=n,
            p=p,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return [
        PrimaryMIDLinkResponse(
            mid_ref=mid["pk"],
            payment_scheme_slug=mid["payment_scheme.slug"],
            mid_value=mid["mid"],
        )
        for mid in mids
    ]


@router.get(
    "/{location_ref}/secondary_mid_location_links",
    response_model=list[SecondaryMIDLinkResponse],
)
async def list_secondary_mid_location_links(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    n: int = Query(default=10),
    p: int = Query(default=1),
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> list[SecondaryMIDLinkResponse]:
    """List Secondary MIDs associated with location."""
    try:
        mids = await db.list_associated_secondary_mids(
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
            location_ref=location_ref,
            n=n,
            p=p,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return [
        SecondaryMIDLinkResponse(
            link_ref=mid["pk"],
            secondary_mid_ref=mid["secondary_mid.pk"],
            payment_scheme_slug=mid["secondary_mid.payment_scheme.slug"],
            secondary_mid_value=mid["secondary_mid.secondary_mid"],
        )
        for mid in mids
    ]


@router.put(
    "/{location_ref}",
    response_model=LocationDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def edit_location(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    fields: LocationDetailMetadata,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> LocationDetailResponse:
    """Edit a locations details"""

    try:
        location = await db.edit_location(
            fields,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
            location_ref=location_ref,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return location
