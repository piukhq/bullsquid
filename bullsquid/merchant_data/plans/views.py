"""Endpoints that operate on plans."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from bullsquid.api.auth import JWTCredentials
from bullsquid.api.errors import APIMultiError, ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, fields_are_unique
from bullsquid.merchant_data import tasks
from bullsquid.merchant_data.auth import AccessLevel, require_access_level
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.db import list_merchants
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.merchants.views import create_merchant_overview_response
from bullsquid.merchant_data.payment_schemes.db import list_payment_schemes
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans import db
from bullsquid.merchant_data.plans.models import (
    CreatePlanRequest,
    PlanCountsResponse,
    PlanDeletionResponse,
    PlanDetailResponse,
    PlanMetadataResponse,
    PlanOverviewResponse,
    PlanPaymentSchemeCountResponse,
)
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.psimis.tables import PSIMI
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from bullsquid.settings import settings

router = APIRouter(prefix="/plans")


async def plan_counts(plan: Plan, payment_scheme: PaymentScheme) -> int:
    primary_mids = await PrimaryMID.count().where(
        PrimaryMID.merchant.plan == plan,
        PrimaryMID.payment_scheme == payment_scheme,
    )
    secondary_mids = await SecondaryMID.count().where(
        SecondaryMID.merchant.plan == plan,
        SecondaryMID.payment_scheme == payment_scheme,
    )
    psimis = await PSIMI.count().where(
        PSIMI.merchant.plan == plan, PSIMI.payment_scheme == payment_scheme
    )
    return primary_mids + secondary_mids + psimis


async def create_plan_overview_response(
    plan: Plan, payment_schemes: list[PaymentScheme]
) -> PlanOverviewResponse:
    """Creates a PlanOverviewResponse instance from the given plan object."""
    merchant_refs = (
        await Merchant.select(Merchant.pk)
        .where(Merchant.plan == plan)
        .output(as_list=True)
    )
    return PlanOverviewResponse(
        plan_ref=plan.pk,
        plan_status=plan.status,
        plan_metadata=PlanMetadataResponse(
            name=plan.name,
            plan_id=plan.plan_id,
            slug=plan.slug,
            icon_url=plan.icon_url,
        ),
        plan_counts=PlanCountsResponse(
            merchants=len(merchant_refs),
            locations=await Location.count().where(Location.merchant.plan == plan),
            payment_schemes=[
                PlanPaymentSchemeCountResponse(
                    slug=payment_scheme.slug,
                    count=await plan_counts(plan, payment_scheme),
                )
                for payment_scheme in payment_schemes
            ],
        ),
        merchant_refs=merchant_refs,
    )


async def create_plan_detail_response(plan: Plan) -> PlanDetailResponse:
    """Creates a PlanDetailResponse instance from the given plan object."""
    # TODO: a way to disable pagination rather than this hack?
    merchants = await list_merchants(plan.pk, n=2**32, p=1)
    payment_schemes = await list_payment_schemes()
    return PlanDetailResponse(
        plan_ref=plan.pk,
        plan_status=plan.status,
        plan_metadata=PlanMetadataResponse(
            name=plan.name, plan_id=plan.plan_id, slug=plan.slug, icon_url=plan.icon_url
        ),
        merchants=[
            await create_merchant_overview_response(merchant, payment_schemes)
            for merchant in merchants
        ],
    )


@router.get("", response_model=list[PlanOverviewResponse])
async def list_plans(
    n: int = Query(default=settings.default_page_size),
    p: int = Query(default=1),
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> list[PlanOverviewResponse]:
    """List all plans."""
    payment_schemes = await list_payment_schemes()
    return [
        await create_plan_overview_response(plan, payment_schemes)
        for plan in await db.list_plans(n=n, p=p)
    ]


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=PlanOverviewResponse
)
async def create_plan(
    plan_data: CreatePlanRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> PlanOverviewResponse:
    """Create a new plan."""
    plan_fields = plan_data.dict()
    if errors := [
        UniqueError(loc=["body", field])
        for field in ("name", "slug", "plan_id")
        if not await fields_are_unique(Plan, {getattr(Plan, field): plan_fields[field]})
    ]:
        raise APIMultiError(errors)

    plan = await db.create_plan(plan_fields)
    return await create_plan_overview_response(plan, await list_payment_schemes())


@router.get("/{plan_ref}", response_model=PlanDetailResponse)
async def get_plan_details(
    plan_ref: UUID,
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> PlanDetailResponse:
    """Get plan details by ref."""
    try:
        plan = await db.get_plan(plan_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex
    return await create_plan_detail_response(plan)


@router.put("/{plan_ref}", response_model=PlanOverviewResponse)
async def update_plan(
    plan_ref: UUID,
    plan_data: CreatePlanRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> PlanOverviewResponse:
    """Update a plan's details."""
    plan_fields = plan_data.dict()
    if errors := [
        UniqueError(loc=["body", field])
        for field in ("name", "slug", "plan_id")
        if not await fields_are_unique(
            Plan, {getattr(Plan, field): plan_fields[field]}, exclude_pk=plan_ref
        )
    ]:
        raise APIMultiError(errors)

    try:
        plan = await db.update_plan(plan_ref, plan_fields)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return await create_plan_overview_response(plan, await list_payment_schemes())


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
