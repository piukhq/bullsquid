"""Database operations for secondary MIDs."""

from uuid import UUID

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.enums import (
    PaymentEnrolmentStatus,
    ResourceStatus,
    TXMStatus,
)
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.db import get_merchant, paginate
from bullsquid.merchant_data.payment_schemes.db import get_payment_scheme
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.models import (
    AssociatedLocationResponse,
    SecondaryMIDMetadata,
    SecondaryMIDResponse,
    UpdateSecondaryMIDRequest,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID


def make_response(secondary_mid: SecondaryMID) -> SecondaryMIDResponse:
    return SecondaryMIDResponse(
        secondary_mid_ref=secondary_mid.pk,
        secondary_mid_metadata=SecondaryMIDMetadata(
            payment_scheme_slug=secondary_mid.payment_scheme.slug,
            secondary_mid=secondary_mid.secondary_mid,
            payment_scheme_store_name=secondary_mid.payment_scheme_store_name,
            payment_enrolment_status=secondary_mid.payment_enrolment_status,
        ),
        secondary_mid_status=secondary_mid.status,
        date_added=secondary_mid.date_added,
        txm_status=secondary_mid.txm_status,
    )


async def list_secondary_mids(
    *, plan_ref: UUID, merchant_ref: UUID, exclude_location: UUID | None, n: int, p: int
) -> list[SecondaryMIDResponse]:
    """Return a list of all secondary MIDs on the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    query = SecondaryMID.objects(SecondaryMID.payment_scheme).where(
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

    results = await paginate(
        query,
        n=n,
        p=p,
    )

    return [make_response(result) for result in results]


async def get_secondary_mid_instance(
    pk: UUID,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> SecondaryMID:
    """Returns a secondary MID."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    secondary_mid = (
        await SecondaryMID.objects(SecondaryMID.payment_scheme)
        .where(
            SecondaryMID.pk == pk,
            SecondaryMID.merchant == merchant,
        )
        .first()
    )
    if not secondary_mid:
        raise NoSuchRecord(SecondaryMID)
    return secondary_mid


async def get_secondary_mid(
    pk: UUID,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> SecondaryMIDResponse:
    """Returns a secondary MID."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    secondary_mid = (
        await SecondaryMID.objects(SecondaryMID.payment_scheme)
        .where(
            SecondaryMID.pk == pk,
            SecondaryMID.merchant == merchant,
        )
        .first()
    )
    if not secondary_mid:
        raise NoSuchRecord(SecondaryMID)

    return make_response(secondary_mid)


async def get_secondary_mids(
    pks: set[UUID],
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> list[SecondaryMIDResponse]:
    """Get a number of secondary MIDs by their primary keys."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    secondary_mids = await SecondaryMID.objects(SecondaryMID.payment_scheme).where(
        SecondaryMID.pk.is_in(list(pks)),
        SecondaryMID.merchant == merchant,
    )

    if len(secondary_mids) != len(pks):
        raise NoSuchRecord(SecondaryMID)

    return [make_response(mid) for mid in secondary_mids]


async def filter_onboarded_secondary_mids(
    secondary_mid_refs: set[UUID],
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> tuple[set[UUID], set[UUID]]:
    """
    Split the given list of secondary MID refs into onboarded and not.
    """
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    q_secondary_mid_refs = list(secondary_mid_refs)

    count = await SecondaryMID.count().where(
        SecondaryMID.pk.is_in(q_secondary_mid_refs)
    )
    if count != len(secondary_mid_refs):
        raise NoSuchRecord(SecondaryMID)

    return {
        result["pk"]
        for result in await SecondaryMID.select(SecondaryMID.pk).where(
            SecondaryMID.pk.is_in(q_secondary_mid_refs),
            SecondaryMID.merchant == merchant,
            SecondaryMID.txm_status == TXMStatus.ONBOARDED,
        )
    }, {
        result["pk"]
        for result in await SecondaryMID.select(SecondaryMID.pk).where(
            SecondaryMID.pk.is_in(q_secondary_mid_refs),
            SecondaryMID.merchant == merchant,
            SecondaryMID.txm_status != TXMStatus.ONBOARDED,
        )
    }


async def create_secondary_mid(
    secondary_mid_data: SecondaryMIDMetadata,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> SecondaryMIDResponse:
    """Create a secondary MID for the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    payment_scheme = await get_payment_scheme(secondary_mid_data.payment_scheme_slug)
    secondary_mid = SecondaryMID(
        secondary_mid=secondary_mid_data.secondary_mid,
        payment_scheme=payment_scheme,
        payment_scheme_store_name=secondary_mid_data.payment_scheme_store_name,
        payment_enrolment_status=secondary_mid_data.payment_enrolment_status,
        merchant=merchant,
    )
    await secondary_mid.save()

    return make_response(secondary_mid)


async def update_secondary_mids_status(
    secondary_mid_refs: set[UUID],
    *,
    status: ResourceStatus,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> None:
    """Updates the status for a list of secondary MIDs on a merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    q_secondary_mid_refs = list(secondary_mid_refs)
    await SecondaryMID.update({SecondaryMID.status: status}).where(
        SecondaryMID.pk.is_in(q_secondary_mid_refs), SecondaryMID.merchant == merchant
    )

    if status == ResourceStatus.DELETED:
        await SecondaryMIDLocationLink.delete().where(
            SecondaryMIDLocationLink.secondary_mid.is_in(q_secondary_mid_refs)
        )


async def list_associated_locations(
    plan_ref: UUID,
    merchant_ref: UUID,
    secondary_mid_ref: UUID,
    *,
    n: int,
    p: int,
) -> list[AssociatedLocationResponse]:
    """List available locations in association with a secondary MID"""
    await get_secondary_mid(
        secondary_mid_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
    )
    results = await paginate(
        SecondaryMIDLocationLink.objects(SecondaryMIDLocationLink.location).where(
            SecondaryMIDLocationLink.secondary_mid == secondary_mid_ref
        ),
        n=n,
        p=p,
    )

    return [
        AssociatedLocationResponse(
            link_ref=result.pk,
            location_ref=result.location.pk,
            location_title=Location(
                name=result.location.name,
                address_line_1=result.location.address_line_1,
                town_city=result.location.town_city,
                postcode=result.location.postcode,
            ).display_text,
        )
        for result in results
    ]


async def update_secondary_mid(
    pk: UUID, fields: UpdateSecondaryMIDRequest, *, plan_ref: UUID, merchant_ref: UUID
) -> SecondaryMIDResponse:
    """Update a secondary MID's editable fields."""
    secondary_mid = await get_secondary_mid_instance(
        pk, plan_ref=plan_ref, merchant_ref=merchant_ref
    )

    for name, value in fields.dict(exclude_unset=True).items():
        setattr(secondary_mid, name, value)
    await secondary_mid.save()

    return make_response(secondary_mid)


async def bulk_update_secondary_mids(
    secondary_mid_refs: set[UUID],
    status: PaymentEnrolmentStatus,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> list[SecondaryMIDResponse]:
    """Update a secondary MID's editable fields."""
    await get_secondary_mids(
        secondary_mid_refs, plan_ref=plan_ref, merchant_ref=merchant_ref
    )

    await SecondaryMID.update({SecondaryMID.payment_enrolment_status: status}).where(
        SecondaryMID.pk.is_in(list(secondary_mid_refs))
    )
    secondary_mids = await get_secondary_mids(
        secondary_mid_refs, plan_ref=plan_ref, merchant_ref=merchant_ref
    )
    return secondary_mids
