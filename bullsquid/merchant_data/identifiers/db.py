"""Database operations for identifiers."""
from uuid import UUID

from bullsquid.merchant_data.db import NoSuchRecord
from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.merchants.db import get_merchant


async def get_identifier(pk: UUID) -> Identifier:
    """Returns an identifier."""
    identifier = await Identifier.objects().get(Identifier.pk == pk)
    if not identifier:
        raise NoSuchRecord

    return identifier


async def filter_onboarded_identifiers(
    identifier_refs: list[UUID], *, plan_ref: UUID, merchant_ref: UUID
) -> tuple[list[UUID], list[UUID]]:
    """
    Split the given list of identifier refs into onboarded and not onboarded/offboarded.
    """
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    # remove duplicates to ensure count mismatches are not caused by duplicate identifiers
    identifier_refs = list(set(identifier_refs))

    count = await Identifier.count().where(Identifier.pk.is_in(identifier_refs))
    if count != len(identifier_refs):
        raise NoSuchRecord

    return [
        result["pk"]
        for result in await Identifier.select(Identifier.pk).where(
            Identifier.pk.is_in(identifier_refs),
            Identifier.merchant == merchant,
            Identifier.txm_status == TXMStatus.ONBOARDED,
        )
    ], [
        result["pk"]
        for result in await Identifier.select(Identifier.pk).where(
            Identifier.pk.is_in(identifier_refs),
            Identifier.merchant == merchant,
            Identifier.txm_status != TXMStatus.ONBOARDED,
        )
    ]


async def update_identifiers_status(
    identifier_refs: list[UUID],
    *,
    status: ResourceStatus,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> None:
    """Updates the status for a list of identifiers on a merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    await Identifier.update({Identifier.status: status}).where(
        Identifier.pk.is_in(identifier_refs), Identifier.merchant == merchant
    )
