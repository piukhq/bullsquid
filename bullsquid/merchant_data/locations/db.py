"""Database access layer for operations on locations"""
from datetime import datetime
from typing import TypedDict
from uuid import UUID

from bullsquid.db import NoSuchRecord, paginate
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.secondary_mids.db import get_secondary_mid
from bullsquid.merchant_data.tables import LocationSecondaryMIDLink

from .tables import Location

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
        "town_city": str | None,
        "postcode": str | None,
        "county": str | None,
        "country": str | None,
        "address_line_2": str | None,
    },
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
        Location.status != ResourceStatus.DELETED,
    )

    if exclude_secondary_mid:
        # validate secondary MID ref
        await get_secondary_mid(
            exclude_secondary_mid, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
        linked_location_pks = (
            await LocationSecondaryMIDLink.select(LocationSecondaryMIDLink.location.pk)
            .where(LocationSecondaryMIDLink.secondary_mid == exclude_secondary_mid)
            .output(as_list=True)
        )
        query = query.where(Location.pk.not_in(linked_location_pks))

    return await paginate(
        query,
        n=n,
        p=p,
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
            Location.status != ResourceStatus.DELETED,
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
            Location.status != ResourceStatus.DELETED,
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
        Location.pk.is_in(location_refs), Location.merchant == merchant
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
