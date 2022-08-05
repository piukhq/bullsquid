"""Database access layer for operations on locations"""
from datetime import datetime
from typing import TypedDict
from uuid import UUID

from bullsquid.db import NoSuchRecord, paginate
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.merchants.db import get_merchant

from .tables import Location

LocationResult = TypedDict(
    "LocationResult",
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
    *, plan_ref: UUID, merchant_ref: UUID, n: int, p: int
) -> list[LocationResult]:
    """Return a list of all locations on the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    return await paginate(
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
        ).where(
            Location.merchant == merchant,
            Location.status != ResourceStatus.DELETED,
        ),
        n=n,
        p=p,
    )


async def get_location(
    location_ref: UUID,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> LocationDetailResult:
    """Return a list of all locations on the given merchant."""
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
