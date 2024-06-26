"""Database access layer for operations on locations"""

from uuid import UUID

from bullsquid.db import NoSuchRecord, paginate
from bullsquid.merchant_data.locations.db import get_location, get_location_instance
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.locations_common.db import (
    create_sub_location_overview_response,
)
from bullsquid.merchant_data.locations_common.models import SubLocationOverviewResponse
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.sub_locations.models import (
    ParentLocation,
    SubLocationDetailMetadata,
    SubLocationDetailResponse,
    SubLocationDetails,
    SubLocationReparentRequest,
    SubLocationReparentResponse,
)


def create_sub_location_detail_metadata(
    location: Location,
) -> SubLocationDetailMetadata:
    """Creates a LocationMetadataResponse instance from the given location object."""
    return SubLocationDetailMetadata(
        name=location.name,
        merchant_internal_id=location.merchant_internal_id,
        is_physical_location=location.is_physical_location,
        address_line_1=location.address_line_1,
        town_city=location.town_city,
        postcode=location.postcode,
        address_line_2=location.address_line_2,
        county=location.county,
        country=location.country,
    )


async def create_sub_location_detail_response(
    location: Location,
) -> SubLocationDetailResponse:
    """Creates a SubLocationDetailResponse instance from the given merchant object."""
    return SubLocationDetailResponse(
        parent_location=ParentLocation(
            location_ref=location.parent.pk,
            location_title=location.parent.display_text,
        ),
        sub_location=SubLocationDetails(
            date_added=location.date_added,
            location_ref=location.pk,
            location_status=location.status,
            location_metadata=create_sub_location_detail_metadata(location),
        ),
    )


async def list_sub_locations(
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
    parent_ref: UUID,
    n: int,
    p: int,
) -> list[SubLocationOverviewResponse]:
    """Return a list of all locations on the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    parent = await get_location_instance(
        location_ref=parent_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
    )

    query = Location.objects().where(
        Location.merchant == merchant,
        Location.parent == parent,
    )

    locations = await paginate(
        query,
        n=n,
        p=p,
    )

    return [
        await create_sub_location_overview_response(location) for location in locations
    ]


async def create_sub_location(
    location_data: SubLocationDetailMetadata,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
    parent: UUID,
) -> SubLocationOverviewResponse:
    """Create and return response for a sub-location."""
    await get_location(
        location_ref=parent, plan_ref=plan_ref, merchant_ref=merchant_ref
    )
    location = Location(
        location_id=None,
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

    return await create_sub_location_overview_response(location)


async def get_sub_location(
    sub_location_ref: UUID,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
    parent_ref: UUID,
) -> SubLocationDetailResponse:
    """Return the details of a location with the given primary key."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    location = await (
        Location.objects(Location.parent)
        .where(
            Location.pk == sub_location_ref,
            Location.merchant == merchant,
            Location.parent == parent_ref,
        )
        .first()
    )
    if not location:
        raise NoSuchRecord(Location)

    return await create_sub_location_detail_response(location)


async def edit_sub_location(
    fields: SubLocationDetailMetadata,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
    location_ref: UUID,
    parent_ref: UUID,
) -> SubLocationDetailResponse:
    """Edit existing sub_location"""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    location = (
        await Location.objects(Location.parent)
        .where(
            Location.pk == location_ref,
            Location.merchant == merchant,
            Location.parent == parent_ref,
        )
        .first()
    )

    if not location:
        raise NoSuchRecord(Location)

    for key, value in fields:
        setattr(location, key, value)
    await location.save()

    return await create_sub_location_detail_response(location)


async def reparent_sub_location(
    sub_location_ref: UUID,
    fields: SubLocationReparentRequest,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
    parent_ref: UUID,
) -> SubLocationReparentResponse:
    """Change or remove the parent of a sub-location."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    location = (
        await Location.objects()
        .where(
            Location.pk == sub_location_ref,
            Location.merchant == merchant,
            Location.parent == parent_ref,
        )
        .first()
    )

    if not location:
        raise NoSuchRecord(Location)

    location.parent = fields.parent_ref

    if fields.parent_ref is None:
        location.location_id = fields.location_id

    await location.save()

    return SubLocationReparentResponse(
        location_ref=location.pk,
        parent_ref=fields.parent_ref,
    )
