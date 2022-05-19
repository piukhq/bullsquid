"""Endpoints that operate on merchants."""

from uuid import UUID

from fastapi import APIRouter

from .db import PrimaryMIDResult, list_primary_mids
from .models import PrimaryMIDListResponse, PrimaryMIDMetadata, PrimaryMIDResponse

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/mids")


async def create_primary_mid_list_response(
    primary_mids: list[PrimaryMIDResult],
) -> PrimaryMIDListResponse:
    """Creates a PrimaryMIDListResponse instance from the given primary MIDs."""
    return PrimaryMIDListResponse(
        mids=[
            PrimaryMIDResponse(
                mid_ref=mid["pk"],
                mid_metadata=PrimaryMIDMetadata(
                    payment_scheme_code=mid["payment_scheme.code"],
                    mid=mid["mid"],
                    visa_bin=mid["visa_bin"],
                    payment_enrolment_status=mid["payment_enrolment_status"],
                ),
                date_added=mid["date_added"],
                txm_status=mid["txm_status"],
            )
            for mid in primary_mids
        ]
    )


@router.get("", response_model=PrimaryMIDListResponse)
async def _(plan_ref: UUID, merchant_ref: UUID) -> PrimaryMIDListResponse:
    """List all primary MIDs for a merchant."""
    mids = await list_primary_mids(plan_ref=plan_ref, merchant_ref=merchant_ref)
    return await create_primary_mid_list_response(mids)
