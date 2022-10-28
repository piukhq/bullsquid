"""Database operations for secondary MIDs."""
from datetime import datetime
from typing import TypedDict
from uuid import UUID

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.enums import (
    PaymentEnrolmentStatus,
    ResourceStatus,
    TXMStatus,
)
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.db import get_merchant, paginate
from bullsquid.merchant_data.payment_schemes.db import get_payment_scheme_by_code
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.models import SecondaryMIDMetadata
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID

SecondaryMIDResult = TypedDict(
    "SecondaryMIDResult",
    {
        "pk": UUID,
        "payment_scheme.code": int,
        "secondary_mid": str,
        "payment_scheme_store_name": str,
        "payment_enrolment_status": PaymentEnrolmentStatus,
        "date_added": datetime,
        "txm_status": TXMStatus,
        "status": ResourceStatus,
    },
)

AssociatedLocationResult = TypedDict(
    "AssociatedLocationResult",
    {
        "pk": str | None,
        "location": str | None,
        "location.name": str,
        "location.address_line_1": str | None,
        "location.town_city": str | None,
        "location.postcode": str | None,
    },
)


async def list_secondary_mids(
    *, plan_ref: UUID, merchant_ref: UUID, exclude_location: UUID | None, n: int, p: int
) -> list[SecondaryMIDResult]:
    """Return a list of all secondary MIDs on the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    query = SecondaryMID.select(
        SecondaryMID.pk,
        SecondaryMID.payment_scheme.code,
        SecondaryMID.secondary_mid,
        SecondaryMID.payment_scheme_store_name,
        SecondaryMID.payment_enrolment_status,
        SecondaryMID.date_added,
        SecondaryMID.txm_status,
        SecondaryMID.status,
    ).where(
        SecondaryMID.merchant == merchant,
    )

    if exclude_location:
        if not await Location.exists().where(
            Location.pk == exclude_location, Location.merchant == merchant
        ):
            raise NoSuchRecord(Location)

        linked_secondary_mid_pks = (
            await SecondaryMIDLocationLink.select(
                SecondaryMIDLocationLink.secondary_mid.pk
            )
            .where(SecondaryMIDLocationLink.location == exclude_location)
            .output(as_list=True)
        )
        if linked_secondary_mid_pks:
            query = query.where(SecondaryMID.pk.not_in(linked_secondary_mid_pks))

    return await paginate(
        query,
        n=n,
        p=p,
    )


async def get_secondary_mid(
    pk: UUID,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> SecondaryMIDResult:
    """Returns a secondary MID."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    secondary_mid = (
        await SecondaryMID.select(
            SecondaryMID.pk,
            SecondaryMID.payment_scheme.code,
            SecondaryMID.secondary_mid,
            SecondaryMID.payment_scheme_store_name,
            SecondaryMID.payment_enrolment_status,
            SecondaryMID.date_added,
            SecondaryMID.txm_status,
            SecondaryMID.status,
        )
        .where(
            SecondaryMID.pk == pk,
            SecondaryMID.merchant == merchant,
        )
        .first()
    )
    if not secondary_mid:
        raise NoSuchRecord(SecondaryMID)

    return secondary_mid


async def filter_onboarded_secondary_mids(
    secondary_mid_refs: list[UUID],
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> tuple[list[UUID], list[UUID]]:
    """
    Split the given list of secondary MID refs into onboarded and not onboarded/offboarded.
    """
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    # remove duplicates to ensure count mismatches are not caused by duplicate secondary MIDs
    secondary_mid_refs = list(set(secondary_mid_refs))

    count = await SecondaryMID.count().where(SecondaryMID.pk.is_in(secondary_mid_refs))
    if count != len(secondary_mid_refs):
        raise NoSuchRecord(SecondaryMID)

    return [
        result["pk"]
        for result in await SecondaryMID.select(SecondaryMID.pk).where(
            SecondaryMID.pk.is_in(secondary_mid_refs),
            SecondaryMID.merchant == merchant,
            SecondaryMID.txm_status == TXMStatus.ONBOARDED,
        )
    ], [
        result["pk"]
        for result in await SecondaryMID.select(SecondaryMID.pk).where(
            SecondaryMID.pk.is_in(secondary_mid_refs),
            SecondaryMID.merchant == merchant,
            SecondaryMID.txm_status != TXMStatus.ONBOARDED,
        )
    ]


async def create_secondary_mid(
    secondary_mid_data: SecondaryMIDMetadata,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> SecondaryMIDResult:
    """Create a secondary MID for the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    payment_scheme = await get_payment_scheme_by_code(
        secondary_mid_data.payment_scheme_code
    )
    secondary_mid = SecondaryMID(
        secondary_mid=secondary_mid_data.secondary_mid,
        payment_scheme=payment_scheme,
        payment_scheme_store_name=secondary_mid_data.payment_scheme_store_name,
        payment_enrolment_status=secondary_mid_data.payment_enrolment_status,
        merchant=merchant,
    )
    await secondary_mid.save()

    return {
        "pk": secondary_mid.pk,
        "payment_scheme.code": payment_scheme.code,
        "secondary_mid": secondary_mid.secondary_mid,
        "payment_scheme_store_name": secondary_mid.payment_scheme_store_name,
        "payment_enrolment_status": PaymentEnrolmentStatus(
            secondary_mid.payment_enrolment_status
        ),
        "date_added": secondary_mid.date_added,
        "txm_status": TXMStatus(secondary_mid.txm_status),
        "status": ResourceStatus(secondary_mid.status),
    }


async def update_secondary_mids_status(
    secondary_mid_refs: list[UUID],
    *,
    status: ResourceStatus,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> None:
    """Updates the status for a list of secondary MIDs on a merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    await SecondaryMID.update({SecondaryMID.status: status}).where(
        SecondaryMID.pk.is_in(secondary_mid_refs), SecondaryMID.merchant == merchant
    )

    if status == ResourceStatus.DELETED:
        await SecondaryMIDLocationLink.delete().where(
            SecondaryMIDLocationLink.secondary_mid.is_in(secondary_mid_refs)
        )


async def list_associated_locations(
    plan_ref: UUID,
    merchant_ref: UUID,
    secondary_mid_ref: UUID,
    *,
    n: int,
    p: int,
) -> list[AssociatedLocationResult]:
    """List available locations in association with a secondary MID"""
    await get_secondary_mid(
        secondary_mid_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
    )
    return await paginate(
        SecondaryMIDLocationLink.select(
            SecondaryMIDLocationLink.pk,
            SecondaryMIDLocationLink.location,
            SecondaryMIDLocationLink.location.name,
            SecondaryMIDLocationLink.location.address_line_1,
            SecondaryMIDLocationLink.location.town_city,
            SecondaryMIDLocationLink.location.postcode,
        ).where(SecondaryMIDLocationLink.secondary_mid == secondary_mid_ref),
        n=n,
        p=p,
    )
