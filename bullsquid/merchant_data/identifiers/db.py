"""Database operations for identifiers."""
from datetime import datetime
from typing import TypedDict
from uuid import UUID

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.identifiers.models import IdentifierMetadata
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.payment_schemes.db import get_payment_scheme_by_code

from .tables import Identifier

IdentifierResult = TypedDict(
    "IdentifierResult",
    {
        "pk": UUID,
        "payment_scheme.code": int,
        "value": str,
        "payment_scheme_merchant_name": str,
        "date_added": datetime,
        "status": ResourceStatus,
    },
)


async def get_identifier(pk: UUID) -> Identifier:
    """Returns an identifier."""
    identifier = await Identifier.objects().get(Identifier.pk == pk)
    if not identifier:
        raise NoSuchRecord(Identifier)

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
        raise NoSuchRecord(Identifier)

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


async def create_identifier(
    identifier_data: IdentifierMetadata,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> IdentifierResult:
    """Create an identifier for the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    payment_scheme = await get_payment_scheme_by_code(
        identifier_data.payment_scheme_code
    )
    identifier = Identifier(
        value=identifier_data.value,
        payment_scheme=payment_scheme,
        payment_scheme_merchant_name=identifier_data.payment_scheme_merchant_name,
        merchant=merchant,
    )
    await identifier.save()

    return {
        "pk": identifier.pk,
        "payment_scheme.code": payment_scheme.code,
        "value": identifier.value,
        "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
        "date_added": identifier.date_added,
        "status": identifier.status,
    }


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
