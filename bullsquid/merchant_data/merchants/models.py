"""Request & response model definitions for merchant endpoints."""
from pydantic import UUID4, validator

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.models import BaseModel
from bullsquid.merchant_data.shared.models import (
    MerchantMetadataResponse,
    PlanMetadataResponse,
)
from bullsquid.merchant_data.validators import FlexibleUrl, string_must_not_be_blank


class CreateMerchantRequest(BaseModel):
    """Merchant request model."""

    name: str
    icon_url: FlexibleUrl | None
    location_label: str

    _ = validator("name", "location_label", allow_reuse=True)(string_must_not_be_blank)


class MerchantDetailResponse(BaseModel):
    """Merchant detail response model."""

    merchant_ref: UUID4
    merchant_status: ResourceStatus
    plan_metadata: PlanMetadataResponse
    merchant_metadata: MerchantMetadataResponse


class MerchantDeletionResponse(BaseModel):
    """Response model for a deletion of a merchant."""

    merchant_status: ResourceStatus
