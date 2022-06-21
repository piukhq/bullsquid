"""Endpoints that operate on merchants."""

from uuid import UUID

from fastapi import APIRouter

from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, field_is_unique
from bullsquid.merchant_data.payment_schemes.db import list_payment_schemes
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.db import get_plan
from bullsquid.merchant_data.plans.models import PlanMetadataResponse
from bullsquid.merchant_data.plans.tables import Plan

from . import db
from .models import (
    CreateMerchantRequest,
    MerchantCountsResponse,
    MerchantDetailResponse,
    MerchantMetadataResponse,
    MerchantOverviewResponse,
    MerchantPaymentSchemeCountResponse,
)
from .tables import Merchant

router = APIRouter(prefix="/plans/{plan_ref}/merchants")


def create_merchant_metadata_response(merchant: Merchant) -> MerchantMetadataResponse:
    """Creates a MerchantMetadataResponse instance from the given merchant object."""
    return MerchantMetadataResponse(
        name=merchant.name,
        icon_url=merchant.icon_url,
        location_label=merchant.location_label,
    )


async def create_merchant_overview_response(
    merchant: Merchant, payment_schemes: list[PaymentScheme]
) -> MerchantOverviewResponse:
    """Creates a MerchantOverviewResponse instance from the given merchant object."""
    return MerchantOverviewResponse(
        merchant_ref=merchant.pk,
        merchant_status=merchant.status,
        merchant_metadata=create_merchant_metadata_response(merchant),
        merchant_counts=MerchantCountsResponse(
            locations=0,
            payment_schemes=[
                MerchantPaymentSchemeCountResponse(
                    label=payment_scheme.label,
                    scheme_code=payment_scheme.code,
                    count=0,
                )
                for payment_scheme in payment_schemes
            ],
        ),
    )


async def create_merchant_detail_response(
    merchant: Merchant, plan: Plan
) -> MerchantDetailResponse:
    """Creates a MerchantDetailResponse instance from the given merchant object."""
    return MerchantDetailResponse(
        merchant_ref=merchant.pk,
        plan_metadata=PlanMetadataResponse(
            name=plan.name,
            plan_id=plan.plan_id,
            slug=plan.slug,
            icon_url=plan.icon_url,
        ),
        merchant_metadata=create_merchant_metadata_response(merchant),
    )


@router.get("", response_model=list[MerchantOverviewResponse])
async def list_merchants(plan_ref: UUID) -> list[MerchantOverviewResponse]:
    """List merchants on a plan."""
    try:
        merchants = await db.list_merchants(plan_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=["path", "plan_ref"], resource_name="Plan"
        ) from ex

    payment_schemes = await list_payment_schemes()
    return [
        await create_merchant_overview_response(merchant, payment_schemes)
        for merchant in merchants
    ]


@router.get("/{merchant_ref}", response_model=MerchantDetailResponse)
async def get_merchant(plan_ref: UUID, merchant_ref: UUID) -> MerchantDetailResponse:
    """Get merchant details."""
    try:
        merchant = await db.get_merchant(merchant_ref, plan_ref=plan_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=["path", "merchant_ref"], resource_name="Merchant"
        ) from ex

    plan = await merchant.get_related(Merchant.plan)
    return await create_merchant_detail_response(merchant, plan)


@router.post("", response_model=MerchantOverviewResponse)
async def create_merchant(plan_ref: UUID, merchant_data: CreateMerchantRequest) -> dict:
    """Add a new merchant to a plan."""
    try:
        plan = await get_plan(plan_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=["path", "plan_ref"], resource_name="Plan"
        ) from ex

    if not await field_is_unique(Merchant, "name", merchant_data.name):
        raise UniqueError(loc=["body", "name"])

    merchant = await db.create_merchant(merchant_data.dict(), plan=plan)

    return await create_merchant_overview_response(
        merchant, await list_payment_schemes()
    )
