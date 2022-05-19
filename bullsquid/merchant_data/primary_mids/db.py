"""Database access layer for primary MID operations."""

from datetime import datetime
from typing import TypedDict
from uuid import UUID

from bullsquid.merchant_data.merchants.db import get_merchant

from .tables import PrimaryMID

PrimaryMIDResult = TypedDict(
    "PrimaryMIDResult",
    {
        "pk": UUID,
        "payment_scheme.code": int,
        "mid": str,
        "visa_bin": str,
        "payment_enrolment_status": str,
        "date_added": datetime,
        "txm_status": str,
    },
)


async def list_primary_mids(
    *, plan_ref: UUID, merchant_ref: UUID
) -> list[PrimaryMIDResult]:
    """Return a list of all primary MIDs on the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    return await PrimaryMID.select(
        PrimaryMID.pk,
        PrimaryMID.payment_scheme.code,
        PrimaryMID.mid,
        PrimaryMID.visa_bin,
        PrimaryMID.payment_enrolment_status,
        PrimaryMID.date_added,
        PrimaryMID.txm_status,
    ).where(PrimaryMID.merchant == merchant)
