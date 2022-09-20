"""Endpoints that operate on locations"""
from uuid import UUID

from fastapi import APIRouter, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, field_is_unique
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.locations import db
from bullsquid.merchant_data.locations.models import (
    AvailablePrimaryMID,
    LocationDeletionRequest,
    LocationDeletionResponse,
    LocationDetailMetadata,
    LocationDetailResponse,
    LocationOverviewMetadata,
    LocationOverviewResponse,
    LocationPaymentSchemeCountResponse,
    PrimaryMIDLinkRequest,
    PrimaryMIDLinkResponse,
    SecondaryMIDLinkRequest,
    SecondaryMIDLinkResponse,
)
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.payment_schemes.db import list_payment_schemes
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.primary_mids.models import LocationLinkResponse
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mid_location_links.db import (
    create_location_primary_mid_links,
    create_secondary_mid_location_links,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/locations")


def create_location_overview_metadata(
    location: db.LocationResult,
) -> LocationOverviewMetadata:
    """Creates a LocationMetadataResponse instance from the given location object."""
    return LocationOverviewMetadata(
        name=location["name"],
        location_id=location["location_id"],
        merchant_internal_id=location["merchant_internal_id"],
        is_physical_location=location["is_physical_location"],
        address_line_1=location["address_line_1"],
        town_city=location["town_city"],
        postcode=location["postcode"],
    )


def create_location_detail_metadata(
    location: db.LocationDetailResult,
) -> LocationDetailMetadata:
    """Creates a LocationMetadataResponse instance from the given location object."""
    return LocationDetailMetadata(
        name=location["name"],
        location_id=location["location_id"],
        merchant_internal_id=location["merchant_internal_id"],
        is_physical_location=location["is_physical_location"],
        address_line_1=location["address_line_1"],
        town_city=location["town_city"],
        postcode=location["postcode"],
        address_line_2=location["address_line_2"],
        county=location["county"],
        country=location["country"],
    )


async def create_location_overview_response(
    location: db.LocationResult, payment_schemes: list[PaymentScheme]
) -> LocationOverviewResponse:
    """Creates a LocationOverviewResponse instance from the given merchant object."""
    return LocationOverviewResponse(
        date_added=location["date_added"],
        location_ref=location["pk"],
        location_status=location["status"],
        location_metadata=create_location_overview_metadata(location),
        payment_schemes=[
            LocationPaymentSchemeCountResponse(
                label=payment_scheme.label,
                scheme_code=payment_scheme.code,
                count=0,
            )
            for payment_scheme in payment_schemes
        ],
    )


async def create_location_detail_response(
    location: db.LocationDetailResult, payment_schemes: list[PaymentScheme]
) -> LocationDetailResponse:
    """Creates a LocationDetailResponse instance from the given merchant object."""
    return LocationDetailResponse(
        date_added=location["date_added"],
        location_ref=location["pk"],
        location_status=location["status"],
        linked_mids_count=0,
        linked_secondary_mids_count=0,
        location_metadata=create_location_detail_metadata(location),
        payment_schemes=[
            LocationPaymentSchemeCountResponse(
                label=payment_scheme.label,
                scheme_code=payment_scheme.code,
                count=0,
            )
            for payment_scheme in payment_schemes
        ],
    )


@router.get("", response_model=list[LocationOverviewResponse])
async def list_locations(
    plan_ref: UUID,
    merchant_ref: UUID,
    exclude_secondary_mid: UUID | None = Query(default=None),
    n: int = Query(default=10),
    p: int = Query(default=1),
) -> list[LocationOverviewResponse]:
    """List locations on a merchant."""
    try:
        locations = await db.list_locations(
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
            exclude_secondary_mid=exclude_secondary_mid,
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
        )

    payment_schemes = await list_payment_schemes()
    return [
        await create_location_overview_response(location, payment_schemes)
        for location in locations
    ]


@router.get("/{location_ref}", response_model=LocationDetailResponse)
async def get_location(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
) -> LocationDetailResponse:
    """Get location details."""
    try:
        location = await db.get_location(
            location_ref, merchant_ref=merchant_ref, plan_ref=plan_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])
    payment_schemes = await list_payment_schemes()
    return await create_location_detail_response(location, payment_schemes)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_location(
    location_data: LocationDetailMetadata, plan_ref: UUID, merchant_ref: UUID
) -> LocationOverviewResponse:
    """Create a location for the given merchant."""
    if not await field_is_unique(Location, "location_id", location_data.location_id):
        raise UniqueError(loc=["body", "location_id"])

    try:
        merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

    location = Location(
        location_id=location_data.location_id,
        name=location_data.name,
        is_physical_location=location_data.is_physical_location,
        address_line_1=location_data.address_line_1,
        address_line_2=location_data.address_line_2,
        town_city=location_data.town_city,
        county=location_data.county,
        country=location_data.country,
        postcode=location_data.postcode,
        merchant_internal_id=location_data.merchant_internal_id,
        merchant=merchant,
    )
    await location.save()

    payment_schemes = await list_payment_schemes()
    return await create_location_overview_response(
        db.LocationResult(
            pk=location.pk,
            status=ResourceStatus(location.status),
            date_added=location.date_added,
            name=location.name,
            location_id=location.location_id,
            merchant_internal_id=location.merchant_internal_id,
            is_physical_location=location.is_physical_location,
            address_line_1=location.address_line_1,
            town_city=location.town_city,
            postcode=location.postcode,
        ),
        payment_schemes,
    )


@router.post(
    "/deletion",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=list[LocationDeletionResponse],
)
async def delete_locations(
    plan_ref: UUID, merchant_ref: UUID, deletion: LocationDeletionRequest
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
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc, plural=plural)

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
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc)

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
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc)

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
) -> list[AvailablePrimaryMID]:
    """returns the list of MIDs that are available for association with a location"""
    try:
        available_mids = await db.list_available_primary_mids(
            plan_ref, merchant_ref=merchant_ref, location_ref=location_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])
    return [
        AvailablePrimaryMID(
            location_link=LocationLinkResponse(
                location_ref=mid["location.pk"],
                location_title=Location.make_title(
                    mid["location.name"],  # type: ignore
                    mid["location.address_line_1"],
                    mid["location.town_city"],
                    mid["location.postcode"],
                ),
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
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

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
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

    return [
        SecondaryMIDLinkResponse(
            link_ref=mid["pk"],
            secondary_mid_ref=mid["secondary_mid.pk"],
            payment_scheme_slug=mid["secondary_mid.payment_scheme.slug"],
            secondary_mid_value=mid["secondary_mid.secondary_mid"],
        )
        for mid in mids
    ]
