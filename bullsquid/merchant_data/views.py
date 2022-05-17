"""Defines endpoints under the /merchants prefix"""
from typing import Any, Type
from uuid import UUID

from fastapi import APIRouter
from piccolo.table import Table

from bullsquid.api.errors import APIMultiError, ResourceNotFoundError, UniqueError
from bullsquid.merchant_data import db, tables
from bullsquid.merchant_data.models import (
    Merchant,
    MerchantCounts,
    MerchantMetadata,
    MerchantPaymentSchemeCount,
    MerchantResponse,
    Plan,
    PlanCounts,
    PlanMetadata,
    PlanPaymentSchemeCount,
    PlanResponse,
    PrimaryMIDListResponse,
    PrimaryMIDMetadata,
    PrimaryMIDResponse,
)

router = APIRouter(prefix="/v1", tags=["Merchant Data Management"])


async def field_is_unique(
    model: Type[Table], field: str, value: Any, *, pk: UUID | None = None
) -> bool:
    """Returns true if the given field on the given table is unique, false otherwise."""
    if value is None:
        # null values are always unique
        return True

    field = getattr(model, field)
    if pk:
        pk_field = getattr(model, "pk")
        return not await model.exists().where(pk_field != pk, field == value)
    return not await model.exists().where(field == value)


async def create_plan_response(
    plan: tables.Plan, payment_schemes: list[tables.PaymentScheme]
) -> PlanResponse:
    """Creates a PlanResponse instance from the given plan object."""
    return PlanResponse(
        plan_ref=plan.pk,
        plan_status=plan.status,
        plan_metadata=PlanMetadata(
            name=plan.name,
            plan_id=plan.plan_id,
            slug=plan.slug,
            icon_url=plan.icon_url,
        ),
        plan_counts=PlanCounts(
            merchants=await db.count_merchants(plan_ref=plan.pk),
            locations=0,
            payment_schemes=[
                PlanPaymentSchemeCount(
                    label=payment_scheme.label,
                    scheme_code=payment_scheme.code,
                    count=0,
                )
                for payment_scheme in payment_schemes
            ],
        ),
    )


async def create_merchant_response(
    merchant: tables.Merchant, payment_schemes: list[tables.PaymentScheme]
) -> MerchantResponse:
    """Creates a MerchantResponse instance from the given merchant object."""
    return MerchantResponse(
        merchant_ref=merchant.pk,
        merchant_status=merchant.status,
        merchant_metadata=MerchantMetadata(
            name=merchant.name,
            icon_url=merchant.icon_url,
            location_label=merchant.location_label,
        ),
        merchant_counts=MerchantCounts(
            locations=0,
            payment_schemes=[
                MerchantPaymentSchemeCount(
                    label=payment_scheme.label,
                    scheme_code=payment_scheme.code,
                    count=0,
                )
                for payment_scheme in payment_schemes
            ],
        ),
    )


async def create_primary_mid_list_response(
    primary_mids: list[db.PrimaryMIDResult],
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


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans() -> list[PlanResponse]:
    """List all plans."""
    payment_schemes = await db.list_payment_schemes()
    return [
        await create_plan_response(plan, payment_schemes)
        for plan in await db.list_plans()
    ]


@router.post("/plans", response_model=PlanResponse)
async def create_plan(plan_data: Plan) -> PlanResponse:
    """Create a new plan."""
    plan_data = plan_data.dict()
    if errors := [
        UniqueError(loc=("body", field))
        for field in ["name", "slug", "plan_id"]
        if not await field_is_unique(db.Plan, field, plan_data[field])
    ]:
        raise APIMultiError(errors)

    plan = await db.create_plan(plan_data)
    return await create_plan_response(plan, await db.list_payment_schemes())


@router.put("/plans/{plan_ref}", response_model=PlanResponse)
async def update_plan(plan_ref: UUID, plan_data: Plan) -> PlanResponse:
    """Update a plan's details."""
    plan_data = plan_data.dict()
    if errors := [
        UniqueError(loc=("body", field))
        for field in ["name", "slug", "plan_id"]
        if not await field_is_unique(db.Plan, field, plan_data[field], pk=plan_ref)
    ]:
        raise APIMultiError(errors)

    try:
        plan = await db.update_plan(plan_ref, plan_data)
    except db.NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=("path", "plan_ref"), resource_name="Plan"
        ) from ex

    return await create_plan_response(plan, await db.list_payment_schemes())


@router.post("/plans/{plan_ref}/merchants", response_model=MerchantResponse)
async def create_merchant(plan_ref: UUID, merchant_data: Merchant) -> dict:
    """Add a new merchant to a plan."""
    try:
        plan = await db.get_plan(plan_ref)
    except db.NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=("path", "plan_ref"), resource_name="Plan"
        ) from ex

    if not await field_is_unique(db.Merchant, "name", merchant_data.name):
        raise UniqueError(loc=("body", "name"))

    merchant = await db.create_merchant(merchant_data.dict(), plan=plan)

    return await create_merchant_response(merchant, await db.list_payment_schemes())


@router.get(
    "/plans/{plan_ref}/merchants/{merchant_ref}/mids",
    response_model=PrimaryMIDListResponse,
)
async def list_primary_mids(
    plan_ref: UUID, merchant_ref: UUID
) -> PrimaryMIDListResponse:
    """List all primary MIDs for a merchant."""
    mids = await db.list_primary_mids(plan_ref=plan_ref, merchant_ref=merchant_ref)
    return await create_primary_mid_list_response(mids)
