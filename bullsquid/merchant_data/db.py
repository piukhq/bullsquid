"""
Global database layer functions that don't belong in any submodule.
"""

from uuid import UUID

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.locations.db import get_location_instance
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from bullsquid.merchant_data.tables import LocationSecondaryMIDLink


async def create_location_primary_mid_links(
    *,
    location_ref: UUID,
    primary_mid_refs: list[UUID],
    plan_ref: UUID,
    merchant_ref: UUID
) -> list[PrimaryMID]:
    """
    Create and return a set of links between locations and primary MIDs.
    """
    location = await get_location_instance(
        location_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
    )

    primary_mid_ref_set = set(primary_mid_refs)
    where = (
        PrimaryMID.pk.is_in(primary_mid_ref_set),
        PrimaryMID.merchant == merchant_ref,
        PrimaryMID.status != ResourceStatus.DELETED,
    )
    primary_mids = await PrimaryMID.objects().where(*where)

    if len(primary_mids) != len(primary_mid_ref_set):
        raise NoSuchRecord(PrimaryMID)

    await PrimaryMID.update({PrimaryMID.location: location}).where(*where)

    return primary_mids


async def create_location_secondary_mid_links(
    *, refs: list[tuple[UUID, UUID]], plan_ref: UUID, merchant_ref: UUID
) -> tuple[list[LocationSecondaryMIDLink], bool]:
    """
    Create a set of links between locations and secondary MIDs.
    Each element of ``refs`` should be a tuple of (location_ref, secondary_mid_ref).
    Returns the created links and a boolean indicating if any links are new.
    """
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    location_refs = {r[0] for r in refs}
    locations = await Location.objects().where(
        Location.pk.is_in(location_refs),
        Location.merchant == merchant,
        Location.status != ResourceStatus.DELETED,
    )

    if len(location_refs) != len(locations):
        raise NoSuchRecord(Location)

    secondary_mid_refs = {r[1] for r in refs}
    secondary_mids = await SecondaryMID.objects().where(
        SecondaryMID.pk.is_in(secondary_mid_refs),
        SecondaryMID.merchant == merchant,
        SecondaryMID.status != ResourceStatus.DELETED,
    )

    if len(secondary_mid_refs) != len(secondary_mids):
        raise NoSuchRecord(SecondaryMID)

    locations_by_pk = {location.pk: location for location in locations}
    secondary_mids_by_pk = {
        secondary_mid.pk: secondary_mid for secondary_mid in secondary_mids
    }

    links = [
        await LocationSecondaryMIDLink.objects(
            LocationSecondaryMIDLink.location,
            LocationSecondaryMIDLink.secondary_mid,
        ).get_or_create(
            (LocationSecondaryMIDLink.location == locations_by_pk[location_ref])
            & (
                LocationSecondaryMIDLink.secondary_mid
                == secondary_mids_by_pk[secondary_mid_ref]
            )
        )
        for location_ref, secondary_mid_ref in refs
    ]

    # TEMP: patch to work around https://github.com/piccolo-orm/piccolo/issues/597
    for link in links:
        if link._was_created:  # pylint: disable=protected-access
            link.location = await link.get_related(LocationSecondaryMIDLink.location)
            link.secondary_mid = await link.get_related(
                LocationSecondaryMIDLink.secondary_mid
            )

    created = any(
        link._was_created for link in links  # pylint: disable=protected-access
    )

    return links, created
