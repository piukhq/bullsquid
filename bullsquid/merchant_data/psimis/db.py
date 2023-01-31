"""Database operations for PSIMIs."""
from datetime import datetime
from typing import TypedDict
from uuid import UUID

from bullsquid.db import NoSuchRecord, paginate
from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.payment_schemes.db import get_payment_scheme
from bullsquid.merchant_data.psimis.models import PSIMIMetadata
from bullsquid.merchant_data.psimis.tables import PSIMI

PSIMIResult = TypedDict(
    "PSIMIResult",
    {
        "pk": UUID,
        "payment_scheme.slug": str,
        "value": str,
        "payment_scheme_merchant_name": str,
        "date_added": datetime,
        "status": ResourceStatus,
    },
)


async def list_psimis(
    *, plan_ref: UUID, merchant_ref: UUID, n: int, p: int
) -> list[PSIMIResult]:
    """Return a list of all PSIMIs on the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    return await paginate(
        PSIMI.select(
            PSIMI.pk,
            PSIMI.payment_scheme.slug,
            PSIMI.value,
            PSIMI.payment_scheme_merchant_name,
            PSIMI.date_added,
            PSIMI.status,
        ).where(
            PSIMI.merchant == merchant,
        ),
        n=n,
        p=p,
    )


async def get_psimi(pk: UUID, *, plan_ref: UUID, merchant_ref: UUID) -> PSIMIResult:
    """Returns a single PSIMI by its PK."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    psimi = (
        await PSIMI.select(
            PSIMI.pk,
            PSIMI.payment_scheme.slug,
            PSIMI.value,
            PSIMI.payment_scheme_merchant_name,
            PSIMI.date_added,
            PSIMI.status,
        )
        .where(
            PSIMI.pk == pk,
            PSIMI.merchant == merchant,
        )
        .first()
    )

    if not psimi:
        raise NoSuchRecord(PSIMI)

    return psimi


async def filter_onboarded_psimis(
    psimi_refs: list[UUID], *, plan_ref: UUID, merchant_ref: UUID
) -> tuple[list[UUID], list[UUID]]:
    """
    Split the given list of PSIMI refs into onboarded and not onboarded/offboarded.
    """
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    # remove duplicates to ensure count mismatches are not caused by duplicate PSIMIs
    psimi_refs = list(set(psimi_refs))

    count = await PSIMI.count().where(PSIMI.pk.is_in(psimi_refs))
    if count != len(psimi_refs):
        raise NoSuchRecord(PSIMI)

    return [
        result["pk"]
        for result in await PSIMI.select(PSIMI.pk).where(
            PSIMI.pk.is_in(psimi_refs),
            PSIMI.merchant == merchant,
            PSIMI.txm_status == TXMStatus.ONBOARDED,
        )
    ], [
        result["pk"]
        for result in await PSIMI.select(PSIMI.pk).where(
            PSIMI.pk.is_in(psimi_refs),
            PSIMI.merchant == merchant,
            PSIMI.txm_status != TXMStatus.ONBOARDED,
        )
    ]


async def create_psimi(
    psimi_data: PSIMIMetadata,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> PSIMIResult:
    """Create an PSIMI for the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    payment_scheme = await get_payment_scheme(psimi_data.payment_scheme_slug)
    psimi = PSIMI(
        value=psimi_data.value,
        payment_scheme=payment_scheme,
        payment_scheme_merchant_name=psimi_data.payment_scheme_merchant_name,
        merchant=merchant,
    )
    await psimi.save()

    return {
        "pk": psimi.pk,
        "payment_scheme.slug": payment_scheme.slug,
        "value": psimi.value,
        "payment_scheme_merchant_name": psimi.payment_scheme_merchant_name,
        "date_added": psimi.date_added,
        "status": ResourceStatus(psimi.status),
    }


async def update_psimi_status(
    psimi_refs: list[UUID],
    *,
    status: ResourceStatus,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> None:
    """Updates the status for a list of PSIMIs on a merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    await PSIMI.update({PSIMI.status: status}).where(
        PSIMI.pk.is_in(psimi_refs), PSIMI.merchant == merchant
    )
