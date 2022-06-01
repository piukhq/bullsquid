"""Endpoints that operate on merchants."""

from uuid import UUID

from fastapi import APIRouter

from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.merchant_data.db import NoSuchRecord, field_is_unique
from bullsquid.merchant_data.payment_schemes.db import list_payment_schemes
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.db import get_plan

from .db import create_merchant, list_merchants
from .models import (
    CreateMerchantRequest,
    MerchantCountsResponse,
    MerchantMetadataResponse,
    MerchantPaymentSchemeCountResponse,
    MerchantResponse,
)
from .tables import Merchant

router = APIRouter(prefix="/plans/{plan_ref}/merchants")


async def create_merchant_response(
    merchant: Merchant, payment_schemes: list[PaymentScheme]
) -> MerchantResponse:
    """Creates a MerchantResponse instance from the given merchant object."""
    return MerchantResponse(
        merchant_ref=merchant.pk,
        merchant_status=merchant.status,
        merchant_metadata=MerchantMetadataResponse(
            name=merchant.name,
            icon_url=merchant.icon_url,
            location_label=merchant.location_label,
        ),
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


@router.get("", response_model=list[MerchantResponse])
async def _(plan_ref: UUID) -> list[dict]:
    """List merchants on a plan."""
    try:
        merchants = await list_merchants(plan_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=["path", "plan_ref"], resource_name="Plan"
        ) from ex

    payment_schemes = await list_payment_schemes()
    return [
        await create_merchant_response(merchant, payment_schemes)
        for merchant in merchants
    ]


@router.post("", response_model=MerchantResponse)
async def _(plan_ref: UUID, merchant_data: CreateMerchantRequest) -> dict:
    """Add a new merchant to a plan."""
    try:
        plan = await get_plan(plan_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=["path", "plan_ref"], resource_name="Plan"
        ) from ex

    if not await field_is_unique(Merchant, "name", merchant_data.name):
        raise UniqueError(loc=["body", "name"])

    merchant = await create_merchant(merchant_data.dict(), plan=plan)

    return await create_merchant_response(merchant, await list_payment_schemes())
