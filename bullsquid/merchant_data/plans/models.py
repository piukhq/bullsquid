"""Request & response model definitions for plan endpoints."""


from pydantic import UUID4, validator

from bullsquid.merchant_data.models import BaseModel
from bullsquid.merchant_data.validators import FlexibleUrl, string_must_not_be_blank


class CreatePlanRequest(BaseModel):
    """Request model for creating/replacing a plan."""

    name: str
    icon_url: FlexibleUrl | None
    slug: str | None
    plan_id: int | None

    _ = validator("name", "slug", allow_reuse=True)(string_must_not_be_blank)


class PlanMetadataResponse(BaseModel):
    """Plan details."""

    name: str
    plan_id: int | None
    slug: str | None
    icon_url: FlexibleUrl | None

    _ = validator("name", "slug", allow_reuse=True)(string_must_not_be_blank)


class PlanPaymentSchemeCountResponse(BaseModel):
    """Counts of MIDs by payment scheme on a plan."""

    label: str
    scheme_code: int
    count: int

    _ = validator("label", allow_reuse=True)(string_must_not_be_blank)


class PlanCountsResponse(BaseModel):
    """Counts of merchants, locations, and MIDs on a plan."""

    merchants: int
    locations: int
    payment_schemes: list[PlanPaymentSchemeCountResponse]


class PlanResponse(BaseModel):
    """Plan response model."""

    plan_ref: UUID4
    plan_status: str
    plan_metadata: PlanMetadataResponse
    plan_counts: PlanCountsResponse

    _ = validator("plan_status", allow_reuse=True)(string_must_not_be_blank)
