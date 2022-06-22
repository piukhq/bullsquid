"""SecondaryMID API views."""
from uuid import UUID

from fastapi import APIRouter, status

from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, field_is_unique
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID

from . import db
from .models import (
    CreateSecondaryMIDRequest,
    SecondaryMIDDeletionListResponse,
    SecondaryMIDDeletionResponse,
    SecondaryMIDMetadata,
    SecondaryMIDResponse,
)

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/secondary_mids")


async def create_secondary_mid_response(
    secondary_mid: db.SecondaryMIDResult,
) -> SecondaryMIDResponse:
    """Creates a SecondaryMIDResponse instance from the given secondary MID."""
    return SecondaryMIDResponse(
        secondary_mid_ref=secondary_mid["pk"],
        secondary_mid_metadata=SecondaryMIDMetadata(
            payment_scheme_code=secondary_mid["payment_scheme.code"],
            secondary_mid=secondary_mid["secondary_mid"],
            payment_scheme_store_name=secondary_mid["payment_scheme_store_name"],
            payment_enrolment_status=secondary_mid["payment_enrolment_status"],
        ),
        secondary_mid_status=secondary_mid["status"],
        date_added=secondary_mid["date_added"],
        txm_status=secondary_mid["txm_status"],
    )


@router.get("", response_model=list[SecondaryMIDResponse])
async def list_secondary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
) -> list[SecondaryMIDResponse]:
    """Lists all secondary MIDs for a merchant."""
    try:
        secondary_mids = await db.list_secondary_mids(
            plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=["path", "merchant_ref"], resource_name="Merchant"
        ) from ex

    return [await create_secondary_mid_response(mid) for mid in secondary_mids]


@router.post("", response_model=SecondaryMIDResponse)
async def create_secondary_mid(
    plan_ref: UUID,
    merchant_ref: UUID,
    secondary_mid_data: CreateSecondaryMIDRequest,
) -> SecondaryMIDResponse:
    """Create a secondary MID for a merchant."""

    if not await field_is_unique(
        SecondaryMID,
        "secondary_mid",
        secondary_mid_data.secondary_mid_metadata.secondary_mid,
    ):
        raise UniqueError(loc=["body", "secondary_mid_metadata", "secondary_mid"])

    try:
        secondary_mid = await db.create_secondary_mid(
            secondary_mid_data.secondary_mid_metadata,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        # the combination of plan & merchant refs did not lead to a merchant.
        raise ResourceNotFoundError(
            loc=["path", "merchant_ref"], resource_name="Merchant"
        ) from ex

    if secondary_mid_data.onboard:
        # TODO: implement once harmonia has support for secondary MID onboarding.
        # await tasks.queue.push(
        #     tasks.OnboardSecondaryMIDs(secondary_mid_refs=[secondary_mid["pk"]])
        # )
        ...

    return await create_secondary_mid_response(secondary_mid)


@router.post("/deletion", status_code=status.HTTP_202_ACCEPTED)
async def delete_secondary_mids(
    plan_ref: UUID, merchant_ref: UUID, secondary_mid_refs: list[UUID]
) -> SecondaryMIDDeletionListResponse:
    """Remove a number of secondary MIDs from a merchant."""
    if not secondary_mid_refs:
        return SecondaryMIDDeletionListResponse(secondary_mids=[])

    try:
        onboarded, not_onboarded = await db.filter_onboarded_secondary_mids(
            secondary_mid_refs, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=["body", "secondary_mid_refs"], resource_name="SecondaryMID"
        ) from ex

    if onboarded:
        await db.update_secondary_mids_status(
            onboarded,
            status=ResourceStatus.PENDING_DELETION,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
        # TODO: implement once Harmonia has secondary MID support.
        # await tasks.queue.push(tasks.OffboardAndDeleteSecondaryMIDs(secondary_mid_refs=onboarded))

    if not_onboarded:
        await db.update_secondary_mids_status(
            not_onboarded,
            status=ResourceStatus.DELETED,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )

    return SecondaryMIDDeletionListResponse(
        secondary_mids=[
            SecondaryMIDDeletionResponse(
                secondary_mid_ref=secondary_mid_ref,
                status=ResourceStatus.PENDING_DELETION,
            )
            for secondary_mid_ref in onboarded
        ]
        + [
            SecondaryMIDDeletionResponse(
                secondary_mid_ref=secondary_mid_ref, status=ResourceStatus.DELETED
            )
            for secondary_mid_ref in not_onboarded
        ]
    )
