"""Endpoints that operate on plans."""

from uuid import UUID

from fastapi import APIRouter

from bullsquid.api.errors import APIMultiError, ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, field_is_unique
from bullsquid.merchant_data.merchants.db import count_merchants
from bullsquid.merchant_data.payment_schemes.db import list_payment_schemes
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme

from . import db
from .models import (
    CreatePlanRequest,
    PlanCountsResponse,
    PlanMetadataResponse,
    PlanPaymentSchemeCountResponse,
    PlanResponse,
)
from .tables import Plan

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
async def list_plans() -> list[PlanResponse]:
    """List all plans."""
    payment_schemes = await list_payment_schemes()
    return [
        await create_plan_response(plan, payment_schemes)
        for plan in await db.list_plans()
    ]


@router.post("", response_model=PlanResponse)
async def create_plan(plan_data: CreatePlanRequest) -> PlanResponse:
    """Create a new plan."""
    plan_data = plan_data.dict()
    if errors := [
        UniqueError(loc=["body", field])
        for field in ["name", "slug", "plan_id"]
        if not await field_is_unique(Plan, field, plan_data[field])
    ]:
        raise APIMultiError(errors)

    plan = await db.create_plan(plan_data)
    return await create_plan_response(plan, await list_payment_schemes())


@router.put("/{plan_ref}", response_model=PlanResponse)
async def update_plan(plan_ref: UUID, plan_data: CreatePlanRequest) -> PlanResponse:
    """Update a plan's details."""
    plan_data = plan_data.dict()
    if errors := [
        UniqueError(loc=["body", field])
        for field in ["name", "slug", "plan_id"]
        if not await field_is_unique(Plan, field, plan_data[field], pk=plan_ref)
    ]:
        raise APIMultiError(errors)

    try:
        plan = await db.update_plan(plan_ref, plan_data)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=("path", "plan_ref"), resource_name="Plan"
        ) from ex

    return await create_plan_response(plan, await list_payment_schemes())
