"""Database access layer for operations on locations"""
from datetime import datetime
from typing import TypedDict
from uuid import UUID

from bullsquid.db import NoSuchRecord, paginate
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.locations.models import (
    LocationDetailMetadata,
    LocationDetailResponse,
    LocationOverviewMetadata,
    LocationOverviewResponse,
    LocationPaymentSchemeCountResponse,
)
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.payment_schemes.db import list_payment_schemes
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID

LocationResult = TypedDict(
    "LocationResult",
    {
        "pk": UUID,
        "status": ResourceStatus,
        "date_added": datetime,
        "name": str | None,
        "location_id": str,
        "merchant_internal_id": str | None,
        "is_physical_location": bool,
        "address_line_1": str | None,
        "town_city": str | None,
        "postcode": str | None,
    },
)

AssociatedPrimaryMIDResult = TypedDict(
    "AssociatedPrimaryMIDResult",
    {
        "pk": UUID,
        "mid": str,
        "payment_scheme.slug": str,
    },
)

AssociatedSecondaryMIDResult = TypedDict(
    "AssociatedSecondaryMIDResult",
    {
        "pk": UUID,
        "secondary_mid.pk": UUID,
        "secondary_mid.secondary_mid": str,
        "secondary_mid.payment_scheme.slug": str,
    },
)

LocationDetailResult = TypedDict(
    "LocationDetailResult",
    {
        "pk": UUID,
        "status": ResourceStatus,
        "date_added": datetime,
        "name": str | None,
        "location_id": str,
        "merchant_internal_id": int | None,
        "is_physical_location": bool,
        "address_line_1": str | None,
        "address_line_2": str | None,
        "town_city": str | None,
        "postcode": str | None,
        "county": str | None,
        "country": str | None,
    },
)

AvailableMIDResult = TypedDict(
    "AvailableMIDResult",
    {
        "pk": UUID,
        "mid": str,
        "payment_scheme.slug": str,
        "location.pk": UUID | None,
        "location.name": str | None,
        "location.address_line_1": str | None,
        "location.town_city": str | None,
        "location.postcode": str | None,
    },
)


def create_location_overview_metadata(
    location: LocationResult,
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
    location: LocationDetailResult,
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
    location: LocationResult, payment_schemes: list[PaymentScheme]
) -> LocationOverviewResponse:
    """Creates a LocationOverviewResponse instance from the given merchant object."""
    return LocationOverviewResponse(
        date_added=location["date_added"],
        location_ref=location["pk"],
        location_status=location["status"],
        location_metadata=create_location_overview_metadata(location),
        payment_schemes=[
            LocationPaymentSchemeCountResponse(
                scheme_slug=payment_scheme.slug,
                count=0,
            )
            for payment_scheme in payment_schemes
        ],
    )


async def create_location_detail_response(
    location: LocationDetailResult, payment_schemes: list[PaymentScheme]
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
                scheme_slug=payment_scheme.slug,
                count=0,
            )
            for payment_scheme in payment_schemes
        ],
    )


async def list_locations(
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
    exclude_secondary_mid: UUID | None,
    n: int,
    p: int,
) -> list[LocationResult]:
    """Return a list of all locations on the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    query = Location.select(
        Location.pk,
        Location.status,
        Location.date_added,
        Location.name,
        Location.location_id,
        Location.merchant_internal_id,
        Location.is_physical_location,
        Location.address_line_1,
        Location.town_city,
        Location.postcode,
    ).where(
        Location.merchant == merchant,
    )

    if exclude_secondary_mid:
        # validate secondary MID ref
        if not await SecondaryMID.exists().where(
            SecondaryMID.pk == exclude_secondary_mid,
            SecondaryMID.merchant == merchant,
        ):
            raise NoSuchRecord(SecondaryMID)

        linked_location_pks = (
            await SecondaryMIDLocationLink.select(SecondaryMIDLocationLink.location.pk)
            .where(SecondaryMIDLocationLink.secondary_mid == exclude_secondary_mid)
            .output(as_list=True)
        )
        if linked_location_pks:
            query = query.where(Location.pk.not_in(linked_location_pks))

    return await paginate(
        query,
        n=n,
        p=p,
    )


async def create_location(
    location_data: LocationDetailMetadata,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
    parent: UUID | None,
) -> LocationOverviewResponse:
    """Create and return response for a location"""
    if parent:
        await get_location(
            location_ref=parent, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    else:
        await get_merchant(merchant_ref, plan_ref=plan_ref)
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
        merchant=merchant_ref,
        parent=parent,
    )
    await location.save()

    payment_schemes = await list_payment_schemes()
    return await create_location_overview_response(
        LocationResult(
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


async def list_available_primary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
) -> list[AvailableMIDResult]:
    """List available mids for association with a location"""
    await get_location(location_ref, plan_ref=plan_ref, merchant_ref=merchant_ref)
    return await PrimaryMID.select(
        PrimaryMID.pk,
        PrimaryMID.mid,
        PrimaryMID.payment_scheme.slug,
        PrimaryMID.location.pk,
        PrimaryMID.location.name,
        PrimaryMID.location.address_line_1,
        PrimaryMID.location.town_city,
        PrimaryMID.location.postcode,
    ).where(
        PrimaryMID.merchant == merchant_ref,
        (PrimaryMID.location != location_ref) | (PrimaryMID.location.is_null()),
    )


async def get_location(
    location_ref: UUID,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> LocationDetailResult:
    """Return the details of a location with the given primary key."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    location = await (
        Location.select(
            Location.pk,
            Location.status,
            Location.date_added,
            Location.name,
            Location.location_id,
            Location.merchant_internal_id,
            Location.is_physical_location,
            Location.address_line_1,
            Location.town_city,
            Location.postcode,
            Location.address_line_2,
            Location.county,
            Location.country,
        )
        .where(
            Location.pk == location_ref,
            Location.merchant == merchant,
        )
        .first()
    )
    if not location:
        raise NoSuchRecord(Location)

    return location


async def get_location_instance(
    location_ref: UUID,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> Location:
    """Return a single location object with the given primary key."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    location = (
        await Location.objects()
        .where(
            Location.pk == location_ref,
            Location.merchant == merchant,
        )
        .first()
    )
    if not location:
        raise NoSuchRecord(Location)

    return location


async def confirm_locations_exist(
    location_refs: list[UUID], *, plan_ref: UUID, merchant_ref: UUID
) -> None:
    """
    Validate that all the given location refs actually exist under the given
    plan and merchant.
    """
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    # remove duplicates to ensure count mismatches are not caused by duplicate locations
    location_refs = list(set(location_refs))

    count = await Location.count().where(
        Location.pk.is_in(location_refs),
        Location.merchant == merchant,
    )
    if count != len(location_refs):
        raise NoSuchRecord(Location)


async def update_locations_status(
    location_refs: list[UUID],
    *,
    status: ResourceStatus,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> None:
    """Updates the status of a list of locations on a merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    await Location.update({Location.status: status}).where(
        Location.pk.is_in(location_refs), Location.merchant == merchant
    )

    if status == ResourceStatus.DELETED:
        await PrimaryMID.update({PrimaryMID.location: None}).where(
            PrimaryMID.location.is_in(location_refs)
        )
        await SecondaryMIDLocationLink.delete().where(
            SecondaryMIDLocationLink.location.is_in(location_refs)
        )


async def list_associated_primary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    n: int,
    p: int,
) -> list[AssociatedPrimaryMIDResult]:
    """List available mids in association with a location"""
    await get_location(location_ref, plan_ref=plan_ref, merchant_ref=merchant_ref)
    return await paginate(
        PrimaryMID.select(
            PrimaryMID.pk,
            PrimaryMID.mid,
            PrimaryMID.payment_scheme.slug,
        ).where(
            PrimaryMID.merchant == merchant_ref,
            (PrimaryMID.location == location_ref),
            PrimaryMID.status != ResourceStatus.DELETED,
        ),
        n=n,
        p=p,
    )


async def list_associated_secondary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    n: int,
    p: int,
) -> list[AssociatedSecondaryMIDResult]:
    """List available secondary mids in association with a location"""
    location = await get_location_instance(
        location_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
    )
    return await paginate(
        SecondaryMIDLocationLink.select(
            SecondaryMIDLocationLink.pk,
            SecondaryMIDLocationLink.secondary_mid.pk,
            SecondaryMIDLocationLink.secondary_mid.payment_scheme.slug,  # type: ignore
            SecondaryMIDLocationLink.secondary_mid.secondary_mid,
        ).where(SecondaryMIDLocationLink.location == location),
        n=n,
        p=p,
    )
