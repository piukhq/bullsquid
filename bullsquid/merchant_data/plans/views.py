"""Endpoints that operate on plans."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from bullsquid.api.auth import JWTCredentials
from bullsquid.api.errors import APIMultiError, ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, field_is_unique
from bullsquid.merchant_data import tasks
from bullsquid.merchant_data.auth import AccessLevel, require_access_level
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.merchants.db import count_merchants
from bullsquid.merchant_data.payment_schemes.db import list_payment_schemes
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans import db
from bullsquid.merchant_data.plans.models import (
    CreatePlanRequest,
    PlanCountsResponse,
    PlanDeletionResponse,
    PlanMetadataResponse,
    PlanPaymentSchemeCountResponse,
    PlanResponse,
)
from bullsquid.merchant_data.plans.tables import Plan

router = APIRouter(prefix="/plans")


async def create_plan_response(
    plan: Plan, payment_schemes: list[PaymentScheme]
) -> PlanResponse:
    """Creates a PlanResponse instance from the given plan object."""
    return PlanResponse(
        plan_ref=plan.pk,
        plan_status=plan.status,
        plan_metadata=PlanMetadataResponse(
            name=plan.name,
            plan_id=plan.plan_id,
            slug=plan.slug,
            icon_url=plan.icon_url,
        ),
        plan_counts=PlanCountsResponse(
            merchants=await count_merchants(plan_ref=plan.pk),
            locations=0,
            payment_schemes=[
                PlanPaymentSchemeCountResponse(
                    label=payment_scheme.label,
                    scheme_code=payment_scheme.code,
                    count=0,
                )
                for payment_scheme in payment_schemes
            ],
        ),
    )


@router.get("", response_model=list[PlanResponse])
async def list_plans(
    n: int = Query(default=10),
    p: int = Query(default=1),
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> list[PlanResponse]:
    """List all plans."""
    payment_schemes = await list_payment_schemes()
    return [
        await create_plan_response(plan, payment_schemes)
        for plan in await db.list_plans(n=n, p=p)
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PlanResponse)
async def create_plan(
    plan_data: CreatePlanRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> PlanResponse:
    """Create a new plan."""
    plan_fields = plan_data.dict()
    if errors := [
        UniqueError(loc=["body", field])
        for field in ("name", "slug", "plan_id")
        if not await field_is_unique(Plan, field, plan_fields[field])
    ]:
        raise APIMultiError(errors)

    plan = await db.create_plan(plan_fields)
    return await create_plan_response(plan, await list_payment_schemes())


@router.get("/{plan_ref}", response_model=PlanResponse)
async def get_plan_details(
    plan_ref: UUID,
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> PlanResponse:
    """Get plan details by ref."""
    try:
        plan = await db.get_plan(plan_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex
    payment_schemes = await list_payment_schemes()
    return await create_plan_response(plan, payment_schemes)


@router.put("/{plan_ref}", response_model=PlanResponse)
async def update_plan(
    plan_ref: UUID,
    plan_data: CreatePlanRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> PlanResponse:
    """Update a plan's details."""
    plan_fields = plan_data.dict()
    if errors := [
        UniqueError(loc=["body", field])
        for field in ("name", "slug", "plan_id")
        if not await field_is_unique(Plan, field, plan_fields[field], pk=plan_ref)
    ]:
        raise APIMultiError(errors)

    try:
        plan = await db.update_plan(plan_ref, plan_fields)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return await create_plan_response(plan, await list_payment_schemes())


@router.delete(
    "/{plan_ref}",
    response_model=PlanDeletionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def delete_plan(
    plan_ref: UUID,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE_DELETE)
    ),
) -> PlanDeletionResponse:
    """
    Delete a plan. All merchants under the plan are also deleted, as well as any
    resources owned by those merchants. Onboarded identifiers are offboarded
    before the deletion completes.

    If there are any onboarded identifiers, this process is run offline via the
    task queue to avoid blocking the client.
    """
    try:
        plan = await db.get_plan(plan_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    if await db.plan_has_onboarded_resources(plan.pk):
        await db.update_plan_status(plan.pk, ResourceStatus.PENDING_DELETION)
        await tasks.queue.push(tasks.OffboardAndDeletePlan(plan_ref=plan.pk))
        return PlanDeletionResponse(plan_status=ResourceStatus.PENDING_DELETION)

    await db.update_plan_status(plan.pk, ResourceStatus.DELETED, cascade=True)
    return PlanDeletionResponse(plan_status=ResourceStatus.DELETED)
