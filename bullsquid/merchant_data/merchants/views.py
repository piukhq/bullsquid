"""Endpoints that operate on merchants."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from bullsquid.api.auth import JWTCredentials
from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, field_is_unique
from bullsquid.merchant_data import tasks
from bullsquid.merchant_data.auth import AccessLevel, require_access_level
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants import db
from bullsquid.merchant_data.merchants.models import (
    CreateMerchantRequest,
    MerchantDeletionResponse,
    MerchantDetailResponse,
    MerchantMetadataResponse,
)
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.db import list_payment_schemes
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.db import get_plan
from bullsquid.merchant_data.plans.models import PlanMetadataResponse
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.shared.models import (
    MerchantCountsResponse,
    MerchantOverviewResponse,
    MerchantPaymentSchemeCountResponse,
)

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
            locations=await Location.count().where(
                Location.merchant == merchant, Location.status != ResourceStatus.DELETED
            ),
            payment_schemes=[
                MerchantPaymentSchemeCountResponse(
                    label=payment_scheme.label,
                    scheme_code=payment_scheme.code,
                    count=await PrimaryMID.count().where(
                        PrimaryMID.merchant == merchant,
                        PrimaryMID.payment_scheme == payment_scheme,
                        PrimaryMID.status != ResourceStatus.DELETED,
                    ),
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
        merchant_status=merchant.status,
        plan_metadata=PlanMetadataResponse(
            name=plan.name,
            plan_id=plan.plan_id,
            slug=plan.slug,
            icon_url=plan.icon_url,
        ),
        merchant_metadata=create_merchant_metadata_response(merchant),
    )


@router.get("", response_model=list[MerchantOverviewResponse])
async def list_merchants(
    plan_ref: UUID,
    n: int = Query(default=10),
    p: int = Query(default=1),
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> list[MerchantOverviewResponse]:
    """List merchants on a plan."""
    try:
        merchants = await db.list_merchants(plan_ref, n=n, p=p)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    payment_schemes = await list_payment_schemes()
    return [
        await create_merchant_overview_response(merchant, payment_schemes)
        for merchant in merchants
    ]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=MerchantOverviewResponse,
)
async def create_merchant(
    plan_ref: UUID,
    merchant_data: CreateMerchantRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> MerchantOverviewResponse:
    """Add a new merchant to a plan."""
    try:
        plan = await get_plan(plan_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    if not await field_is_unique(Merchant, "name", merchant_data.name):
        raise UniqueError(loc=["body", "name"])

    merchant = await db.create_merchant(merchant_data.dict(), plan=plan)

    return await create_merchant_overview_response(
        merchant, await list_payment_schemes()
    )


@router.get("/{merchant_ref}", response_model=MerchantDetailResponse)
async def get_merchant(
    plan_ref: UUID,
    merchant_ref: UUID,
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> MerchantDetailResponse:
    """Get merchant details."""
    try:
        merchant = await db.get_merchant(merchant_ref, plan_ref=plan_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    plan = await merchant.get_related(Merchant.plan)
    return await create_merchant_detail_response(merchant, plan)


@router.put("/{merchant_ref}", response_model=MerchantOverviewResponse)
async def update_merchant(
    plan_ref: UUID,
    merchant_ref: UUID,
    merchant_data: CreateMerchantRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> MerchantOverviewResponse:
    """Update a merchant with new details."""

    if not await field_is_unique(Merchant, "name", merchant_data.name, pk=merchant_ref):
        raise UniqueError(loc=["body", "name"])

    try:
        merchant = await db.update_merchant(
            merchant_ref, merchant_data, plan_ref=plan_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return await create_merchant_overview_response(
        merchant, await list_payment_schemes()
    )


@router.delete(
    "/{merchant_ref}",
    response_model=MerchantDeletionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def delete_merchant(
    plan_ref: UUID,
    merchant_ref: UUID,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE_DELETE)
    ),
) -> MerchantDeletionResponse:
    """
    Mark a merchant as deleted, also deleting its associated resources.
    """

    try:
        merchant = await db.get_merchant(merchant_ref, plan_ref=plan_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    if await db.merchant_has_onboarded_resources(merchant.pk):
        await db.update_merchant_status(merchant.pk, ResourceStatus.PENDING_DELETION)
        await tasks.queue.push(
            tasks.OffboardAndDeleteMerchant(merchant_ref=merchant.pk)
        )
        return MerchantDeletionResponse(merchant_status=ResourceStatus.PENDING_DELETION)

    await db.update_merchant_status(merchant.pk, ResourceStatus.DELETED, cascade=True)
    return MerchantDeletionResponse(merchant_status=ResourceStatus.DELETED)
