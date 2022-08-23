"""Endpoints that operate on locations"""
from uuid import UUID

from fastapi import APIRouter, Query, status

from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, field_is_unique
from bullsquid.merchant_data.db import create_location_secondary_mid_links
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.merchants.models import MerchantOverviewResponse
from bullsquid.merchant_data.payment_schemes.db import list_payment_schemes
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID

from . import db
from .models import (
    LocationDeletionRequest,
    LocationDeletionResponse,
    LocationDetailMetadata,
    LocationDetailResponse,
    LocationOverviewMetadata,
    LocationOverviewResponse,
    LocationPaymentSchemeCountResponse,
    SecondaryMIDLinkRequest,
    SecondaryMIDLinkResponse,
)
from .tables import Location

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
    """Creates a MerchantOverviewResponse instance from the given merchant object."""
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
    """Creates a MerchantOverviewResponse instance from the given merchant object."""
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
    n: int = Query(default=10),
    p: int = Query(default=1),
) -> list[MerchantOverviewResponse]:
    """List locations on a merchant."""
    try:
        locations = await db.list_locations(
            plan_ref=plan_ref, merchant_ref=merchant_ref, n=n, p=p
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

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
) -> MerchantOverviewResponse:
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
            status=location.status,
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
    "/{location_ref}/secondary_mid_location_links",
    response_model=list[SecondaryMIDLinkResponse],
)
async def link_location_to_secondary_mid(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    link_request: SecondaryMIDLinkRequest,
) -> list[SecondaryMIDLinkResponse]:
    """
    Link a secondary MID to a location.
    """
    try:
        links = await create_location_secondary_mid_links(
            refs=[
                (location_ref, secondary_mid_ref)
                for secondary_mid_ref in link_request.secondary_mid_refs
            ],
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        loc = ["body"] if ex.table == SecondaryMID else ["path"]
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc)

    return [
        SecondaryMIDLinkResponse(
            link_ref=link.pk,
            secondary_mid_ref=link.secondary_mid.pk,
            payment_scheme_slug=link.secondary_mid.payment_scheme,
            secondary_mid_value=link.secondary_mid.secondary_mid,
        )
        for link in links
    ]
