"""Identifier API views."""
from uuid import UUID

from fastapi import APIRouter, status

from bullsquid.api.errors import ResourceNotFoundError
from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.enums import ResourceStatus

from . import db
from .models import IdentifierDeletionListResponse, IdentifierDeletionResponse

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/identifiers")


@router.post("/deletion", status_code=status.HTTP_202_ACCEPTED)
async def delete_identifiers(
    plan_ref: UUID, merchant_ref: UUID, identifier_refs: list[UUID]
) -> IdentifierDeletionListResponse:
    """Remove a number of identifiers from a merchant."""
    if not identifier_refs:
        return IdentifierDeletionListResponse(identifiers=[])

    try:
        onboarded, not_onboarded = await db.filter_onboarded_identifiers(
            identifier_refs, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=["body", "identifier_refs"], resource_name="Identifier"
        ) from ex

    if onboarded:
        await db.update_identifiers_status(
            onboarded,
            status=ResourceStatus.PENDING_DELETION,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
        # TODO: implement once Harmonia has identifier/PSIMI support.
        # await tasks.queue.push(tasks.OffboardAndDeleteIdentifiers(identifier_refs=onboarded))

    if not_onboarded:
        await db.update_identifiers_status(
            not_onboarded,
            status=ResourceStatus.DELETED,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )

    return IdentifierDeletionListResponse(
        identifiers=[
            IdentifierDeletionResponse(
                identifier_ref=identifier_ref, status=ResourceStatus.PENDING_DELETION
            )
            for identifier_ref in onboarded
        ]
        + [
            IdentifierDeletionResponse(
                identifier_ref=identifier_ref, status=ResourceStatus.DELETED
            )
            for identifier_ref in not_onboarded
        ]
    )
