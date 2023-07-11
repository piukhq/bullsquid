"""Request & response model definitions for plan endpoints."""


from pydantic import UUID4, constr, validator

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.models import BaseModel
from bullsquid.merchant_data.shared.models import (
    MerchantOverviewResponse,
    PlanMetadataResponse,
)
from bullsquid.merchant_data.validators import (
    FlexibleUrl,
    nullify_blank_strings,
    string_must_not_be_blank,
)


class CreatePlanRequest(BaseModel):
    """Request model for creating/replacing a plan."""

    name: str
    icon_url: FlexibleUrl | None
    slug: constr(regex=("^[a-z0-9]+(?:-[a-z0-9]+)*$")) | None
    plan_id: int | None

    _ = validator("name", allow_reuse=True)(string_must_not_be_blank)
    _ = validator("slug", allow_reuse=True)(nullify_blank_strings)


class PlanPaymentSchemeCountResponse(BaseModel):
    """Counts of MIDs by payment scheme on a plan."""

    slug: str
    count: int

    _ = validator("slug", allow_reuse=True)(string_must_not_be_blank)


class PlanCountsResponse(BaseModel):
    """Counts of merchants, locations, and MIDs on a plan."""

    merchants: int
    locations: int
    payment_schemes: list[PlanPaymentSchemeCountResponse]


class PlanOverviewResponse(BaseModel):
    """Plan overview response model."""

    plan_ref: UUID4
    plan_status: ResourceStatus
    plan_metadata: PlanMetadataResponse
    plan_counts: PlanCountsResponse
    merchant_refs: list[UUID4]

    _ = validator("plan_status", allow_reuse=True)(string_must_not_be_blank)


class PlanDetailResponse(BaseModel):
    """Plan detail response model."""

    plan_ref: UUID4
    plan_status: ResourceStatus
    plan_metadata: PlanMetadataResponse
    merchants: list[MerchantOverviewResponse]


class PlanDeletionResponse(BaseModel):
    """Response model for the deletion of a plan."""

    plan_status: ResourceStatus
