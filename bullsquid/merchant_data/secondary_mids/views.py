"""SecondaryMID API views."""
from uuid import UUID

from fastapi import APIRouter, status

from bullsquid.api.errors import ResourceNotFoundError
from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.enums import ResourceStatus

from . import db
from .models import SecondaryMIDDeletionListResponse, SecondaryMIDDeletionResponse

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/secondary_mids")


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
