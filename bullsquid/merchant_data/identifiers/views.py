"""Identifier API views."""
from uuid import UUID

from fastapi import APIRouter, status

from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, field_is_unique
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan

from . import db
from .models import (
    CreateIdentifierRequest,
    IdentifierDeletionListResponse,
    IdentifierDeletionResponse,
    IdentifierMetadata,
    IdentifierResponse,
)

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/identifiers")


def create_identifier_response(identifier: db.IdentifierResult) -> IdentifierResponse:
    """Creates an IdentifierResponse instance from the given identifier."""
    return IdentifierResponse(
        identifier_ref=identifier["pk"],
        identifier_metadata=IdentifierMetadata(
            value=identifier["value"],
            payment_scheme_merchant_name=identifier["payment_scheme_merchant_name"],
            payment_scheme_code=identifier["payment_scheme.code"],
        ),
        identifier_status=identifier["status"],
        date_added=identifier["date_added"],
    )


@router.get("", response_model=list[IdentifierResponse])
async def list_identifiers(
    plan_ref: UUID,
    merchant_ref: UUID,
) -> list[IdentifierResponse]:
    """List all identifiers for a merchant."""
    try:
        identifiers = await db.list_identifiers(
            plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

    return [create_identifier_response(identifier) for identifier in identifiers]


@router.get("/{identifier_ref}", response_model=IdentifierResponse)
async def get_identifier_details(
    plan_ref: UUID, merchant_ref: UUID, identifier_ref: UUID
) -> IdentifierResponse:
    """Returns details of a single identifier."""
    try:
        mid = await db.get_identifier(
            identifier_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

    return create_identifier_response(mid)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=IdentifierResponse)
async def create_identifier(
    plan_ref: UUID,
    merchant_ref: UUID,
    identifier_data: CreateIdentifierRequest,
) -> IdentifierResponse:
    """Create an identifier for a merchant."""

    if not await field_is_unique(
        Identifier, "value", identifier_data.identifier_metadata.value
    ):
        raise UniqueError(loc=["body", "identifier_metadata", "value"])

    try:
        identifier = await db.create_identifier(
            identifier_data.identifier_metadata,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        loc = (
            ["path"]
            if ex.table in [Plan, Merchant]
            else ["body", "identifier_metadata"]
        )
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc)

    if identifier_data.onboard:
        # TODO: implement once harmonia has support for identifier onboarded.
        # await tasks.queue.push(
        #     tasks.OnboardIdentifiers(identifier_refs=[identifier["pk"]])
        # )
        ...

    return create_identifier_response(identifier)


@router.post(
    "/deletion",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IdentifierDeletionListResponse,
)
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
        plural = ex.table == Identifier
        loc = ["body"] if ex.table == Identifier else ["path"]
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc, plural=plural)

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
