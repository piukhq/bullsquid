"""PSIMI API views."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from bullsquid.api.auth import AccessLevel, JWTCredentials
from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, fields_are_unique
from bullsquid.merchant_data.auth import require_access_level
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.psimis import db
from bullsquid.merchant_data.psimis.models import (
    CreatePSIMIRequest,
    PSIMIDeletionRequest,
    PSIMIDeletionResponse,
    PSIMIResponse,
)
from bullsquid.merchant_data.psimis.tables import PSIMI
from bullsquid.settings import settings

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/psimis")


@router.get("", response_model=list[PSIMIResponse])
async def list_psimis(
    plan_ref: UUID,
    merchant_ref: UUID,
    n: int = Query(default=settings.default_page_size),
    p: int = Query(default=1),
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> list[PSIMIResponse]:
    """List all PSIMIs for a merchant."""
    try:
        psimis = await db.list_psimis(
            plan_ref=plan_ref, merchant_ref=merchant_ref, n=n, p=p
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

    return psimis


@router.get("/{psimi_ref}", response_model=PSIMIResponse)
async def get_psimi_details(
    plan_ref: UUID,
    merchant_ref: UUID,
    psimi_ref: UUID,
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> PSIMIResponse:
    """Returns details of a single PSIMI."""
    try:
        psimi = await db.get_psimi(
            psimi_ref,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

    return psimi


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PSIMIResponse)
async def create_psimi(
    plan_ref: UUID,
    merchant_ref: UUID,
    psimi_data: CreatePSIMIRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> PSIMIResponse:
    """Create an PSIMI for a merchant."""

    if not await fields_are_unique(
        PSIMI, {PSIMI.value: psimi_data.psimi_metadata.value}
    ):
        raise UniqueError(loc=["body", "psimi_metadata", "value"])

    try:
        psimi = await db.create_psimi(
            psimi_data.psimi_metadata,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        loc = ["path"] if ex.table in (Plan, Merchant) else ["body", "psimi_metadata"]
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc) from ex

    if psimi_data.onboard:
        # TODO: implement once harmonia has support for PSIMI onboarding.
        # await tasks.queue.push(
        #     tasks.OnboardPSIMIs(psimi_refs=[psimi["pk"]])
        # )
        ...

    return psimi


@router.post(
    "/deletion",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=list[PSIMIDeletionResponse],
)
async def delete_psimis(
    plan_ref: UUID,
    merchant_ref: UUID,
    deletion: PSIMIDeletionRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE_DELETE)
    ),
) -> list[PSIMIDeletionResponse]:
    """Remove a number of PSIMIs from a merchant."""
    if not deletion.psimi_refs:
        return []

    try:
        onboarded, not_onboarded = await db.filter_onboarded_psimis(
            deletion.psimi_refs, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        plural = ex.table == PSIMI
        loc = ["body"] if ex.table == PSIMI else ["path"]
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc, plural=plural)

    if onboarded:
        await db.update_psimi_status(
            onboarded,
            status=ResourceStatus.PENDING_DELETION,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
        # TODO: implement once Harmonia has PSIMI support.
        # await tasks.queue.push(tasks.OffboardAndDeletePSIMIs(psimi_refs=onboarded))

    if not_onboarded:
        await db.update_psimi_status(
            not_onboarded,
            status=ResourceStatus.DELETED,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )

    return [
        PSIMIDeletionResponse(
            psimi_ref=psimi_ref, status=ResourceStatus.PENDING_DELETION
        )
        for psimi_ref in onboarded
    ] + [
        PSIMIDeletionResponse(psimi_ref=psimi_ref, status=ResourceStatus.DELETED)
        for psimi_ref in not_onboarded
    ]
