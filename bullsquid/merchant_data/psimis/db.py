"""Database operations for PSIMIs."""
from uuid import UUID

from bullsquid.db import NoSuchRecord, paginate
from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.payment_schemes.db import get_payment_scheme
from bullsquid.merchant_data.psimis.models import PSIMIMetadata, PSIMIResponse
from bullsquid.merchant_data.psimis.tables import PSIMI


def make_response(psimi: PSIMI) -> PSIMIResponse:
    return PSIMIResponse(
        psimi_ref=psimi.pk,
        psimi_metadata=PSIMIMetadata(
            value=psimi.value,
            payment_scheme_merchant_name=psimi.payment_scheme_merchant_name,
            payment_scheme_slug=psimi.payment_scheme.slug,
        ),
        psimi_status=psimi.status,
        date_added=psimi.date_added,
    )


async def list_psimis(
    *, plan_ref: UUID, merchant_ref: UUID, n: int, p: int
) -> list[PSIMIResponse]:
    """Return a list of all PSIMIs on the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    results = await paginate(
        PSIMI.objects(PSIMI.payment_scheme).where(
            PSIMI.merchant == merchant,
        ),
        n=n,
        p=p,
    )

    return [make_response(result) for result in results]


async def get_psimi(pk: UUID, *, plan_ref: UUID, merchant_ref: UUID) -> PSIMIResponse:
    """Returns a single PSIMI by its PK."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    psimi = (
        await PSIMI.objects(PSIMI.payment_scheme)
        .where(
            PSIMI.pk == pk,
            PSIMI.merchant == merchant,
        )
        .first()
    )

    if not psimi:
        raise NoSuchRecord(PSIMI)

    return make_response(psimi)


async def get_psimis(
    pks: set[UUID],
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> list[PSIMIResponse]:
    """Get a number of PSIMIS by their primary keys."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    psimis = await PSIMI.objects(PSIMI.payment_scheme).where(
        PSIMI.pk.is_in(list(pks)),
        PSIMI.merchant == merchant,
    )

    if len(psimis) != len(pks):
        raise NoSuchRecord(PSIMI)

    return [make_response(psimi) for psimi in psimis]


async def filter_onboarded_psimis(
    psimi_refs: set[UUID], *, plan_ref: UUID, merchant_ref: UUID
) -> tuple[set[UUID], set[UUID]]:
    """
    Split the given list of PSIMI refs into onboarded and not onboarded/offboarded.
    """
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    q_psimi_refs = list(psimi_refs)

    count = await PSIMI.count().where(PSIMI.pk.is_in(q_psimi_refs))
    if count != len(psimi_refs):
        raise NoSuchRecord(PSIMI)

    return {
        result["pk"]
        for result in await PSIMI.select(PSIMI.pk).where(
            PSIMI.pk.is_in(q_psimi_refs),
            PSIMI.merchant == merchant,
            PSIMI.txm_status == TXMStatus.ONBOARDED,
        )
    }, {
        result["pk"]
        for result in await PSIMI.select(PSIMI.pk).where(
            PSIMI.pk.is_in(q_psimi_refs),
            PSIMI.merchant == merchant,
            PSIMI.txm_status != TXMStatus.ONBOARDED,
        )
    }


async def create_psimi(
    psimi_data: PSIMIMetadata,
    *,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> PSIMIResponse:
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

    return make_response(psimi)


async def update_psimi_status(
    psimi_refs: set[UUID],
    *,
    status: ResourceStatus,
    plan_ref: UUID,
    merchant_ref: UUID,
) -> None:
    """Updates the status for a list of PSIMIs on a merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)
    await PSIMI.update({PSIMI.status: status}).where(
        PSIMI.pk.is_in(list(psimi_refs)), PSIMI.merchant == merchant
    )
