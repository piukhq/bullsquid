"""
Database layer for functions that operate on secondary MID location links.
"""

from uuid import UUID

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.locations.db import get_location_instance
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID


async def create_location_primary_mid_links(
    *,
    location_ref: UUID,
    primary_mid_refs: set[UUID],
    plan_ref: UUID,
    merchant_ref: UUID,
) -> list[PrimaryMID]:
    """
    Create and return a set of links between locations and primary MIDs.
    """
    location = await get_location_instance(
        location_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
    )

    where = (
        PrimaryMID.pk.is_in(list(primary_mid_refs)),
        PrimaryMID.merchant == merchant_ref,
    )
    primary_mids = await PrimaryMID.objects().where(*where)

    if len(primary_mids) != len(primary_mid_refs):
        raise NoSuchRecord(PrimaryMID)

    await PrimaryMID.update({PrimaryMID.location: location}).where(*where)

    return primary_mids


async def create_secondary_mid_location_links(
    *, refs: list[tuple[UUID, UUID]], plan_ref: UUID, merchant_ref: UUID
) -> tuple[list[SecondaryMIDLocationLink], bool]:
    """
    Create a set of links between secondary MIDs and locations .
    Each element of ``refs`` should be a tuple of (secondary_mid_ref, location_ref).
    Returns the created links and a boolean indicating if any links are new.
    """
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    secondary_mid_refs = list({r[0] for r in refs})
    secondary_mids = await SecondaryMID.objects().where(
        SecondaryMID.pk.is_in(secondary_mid_refs),
        SecondaryMID.merchant == merchant,
    )

    if len(secondary_mid_refs) != len(secondary_mids):
        raise NoSuchRecord(SecondaryMID)

    location_refs = list({r[1] for r in refs})
    locations = await Location.objects().where(
        Location.pk.is_in(location_refs),
        Location.merchant == merchant,
        Location.parent.is_null(),
    )

    if len(location_refs) != len(locations):
        raise NoSuchRecord(Location)

    secondary_mids_by_pk = {
        secondary_mid.pk: secondary_mid for secondary_mid in secondary_mids
    }
    locations_by_pk = {location.pk: location for location in locations}

    links = [
        await SecondaryMIDLocationLink.objects(
            SecondaryMIDLocationLink.secondary_mid,
            SecondaryMIDLocationLink.location,
        ).get_or_create(
            (
                SecondaryMIDLocationLink.secondary_mid
                == secondary_mids_by_pk[secondary_mid_ref]
            )
            & (SecondaryMIDLocationLink.location == locations_by_pk[location_ref])
        )
        for secondary_mid_ref, location_ref in refs
    ]

    # TEMP: patch to work around https://github.com/piccolo-orm/piccolo/issues/597
    for link in links:
        if link._was_created:  # pylint: disable=protected-access
            link.location = await link.get_related(SecondaryMIDLocationLink.location)
            link.secondary_mid = await link.get_related(
                SecondaryMIDLocationLink.secondary_mid
            )

    created = any(
        link._was_created
        for link in links  # pylint: disable=protected-access
    )

    return links, created


async def delete_secondary_mid_location_link(
    link_ref: UUID, *, plan_ref: UUID, merchant_ref: UUID
) -> None:
    """
    Delete the link between a secondary MID and location.
    """

    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    link = await SecondaryMIDLocationLink.objects(
        SecondaryMIDLocationLink.secondary_mid, SecondaryMIDLocationLink.location
    ).get(SecondaryMIDLocationLink.pk == link_ref)

    if (
        link is None
        or link.secondary_mid.merchant != merchant.pk
        or link.location.merchant != merchant.pk
    ):
        raise NoSuchRecord(SecondaryMIDLocationLink)

    await link.remove()
