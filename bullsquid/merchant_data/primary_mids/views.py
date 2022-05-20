"""Endpoints that operate on merchants."""

from uuid import UUID

from fastapi import APIRouter

from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.merchant_data.db import NoSuchRecord, field_is_unique

from .db import PrimaryMIDResult, create_primary_mid, list_primary_mids
from .models import (
    CreatePrimaryMIDRequest,
    PrimaryMIDListResponse,
    PrimaryMIDMetadata,
    PrimaryMIDResponse,
)
from .tables import PrimaryMID

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/mids")


async def create_primary_mid_response(
    primary_mid: PrimaryMIDResult,
) -> PrimaryMIDResponse:
    """Creates a PrimaryMIDResponse instance from the given primary MID."""
    return PrimaryMIDResponse(
        mid_ref=primary_mid["pk"],
        mid_metadata=PrimaryMIDMetadata(
            payment_scheme_code=primary_mid["payment_scheme.code"],
            mid=primary_mid["mid"],
            visa_bin=primary_mid["visa_bin"],
            payment_enrolment_status=primary_mid["payment_enrolment_status"],
        ),
        date_added=primary_mid["date_added"],
        txm_status=primary_mid["txm_status"],
    )


async def create_primary_mid_list_response(
    primary_mids: list[PrimaryMIDResult],
) -> PrimaryMIDListResponse:
    """Creates a PrimaryMIDListResponse instance from the given primary MIDs."""
    return PrimaryMIDListResponse(
        mids=[await create_primary_mid_response(mid) for mid in primary_mids]
    )


@router.get("", response_model=PrimaryMIDListResponse)
async def _(plan_ref: UUID, merchant_ref: UUID) -> PrimaryMIDListResponse:
    """List all primary MIDs for a merchant."""
    try:
        mids = await list_primary_mids(plan_ref=plan_ref, merchant_ref=merchant_ref)
    except NoSuchRecord as ex:
        # the combination of plan & merchant refs did not lead to a merchant.
        raise ResourceNotFoundError(
            loc=["path", "merchant_ref"], resource_name="Merchant"
        ) from ex

    return await create_primary_mid_list_response(mids)


@router.post("", response_model=PrimaryMIDResponse)
async def _(
    plan_ref: UUID, merchant_ref: UUID, mid_data: CreatePrimaryMIDRequest
) -> PrimaryMIDResponse:
    """Create a primary MID for a merchant."""

    if not await field_is_unique(PrimaryMID, "mid", mid_data.mid_metadata.mid):
        raise UniqueError(loc=["body", "mid_metadata", "mid"])

    try:
        mid = await create_primary_mid(
            mid_data.mid_metadata, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        # the combination of plan & merchant refs did not lead to a merchant.
        raise ResourceNotFoundError(
            loc=["path", "merchant_ref"], resource_name="Merchant"
        ) from ex

    return await create_primary_mid_response(mid)
