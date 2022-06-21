"""Request & response model definitions for merchant endpoints."""
from pydantic import UUID4, validator

from bullsquid.merchant_data.models import BaseModel
from bullsquid.merchant_data.plans.models import PlanMetadataResponse
from bullsquid.merchant_data.validators import FlexibleUrl, string_must_not_be_blank


class CreateMerchantRequest(BaseModel):
    """Merchant request model."""

    name: str
    icon_url: FlexibleUrl | None
    location_label: str

    _ = validator("name", "location_label", allow_reuse=True)(string_must_not_be_blank)


class MerchantMetadataResponse(BaseModel):
    """Merchant details response model."""

    name: str
    icon_url: FlexibleUrl | None
    location_label: str

    _ = validator("name", "location_label", allow_reuse=True)(string_must_not_be_blank)


class MerchantPaymentSchemeCountResponse(BaseModel):
    """Counts of MIDs by payment scheme on a merchant."""

    label: str
    scheme_code: int
    count: int

    _ = validator("label", allow_reuse=True)(string_must_not_be_blank)


class MerchantCountsResponse(BaseModel):
    """Counts of merchants, locations, and MIDs on a merchant."""

    locations: int
    payment_schemes: list[MerchantPaymentSchemeCountResponse]


class MerchantOverviewResponse(BaseModel):
    """Merchant response model."""

    merchant_ref: UUID4
    merchant_status: str
    merchant_metadata: MerchantMetadataResponse
    merchant_counts: MerchantCountsResponse

    _ = validator("merchant_status", allow_reuse=True)(string_must_not_be_blank)


class MerchantDetailResponse(BaseModel):
    """Merchant detail response model."""

    merchant_ref: UUID4
    plan_metadata: PlanMetadataResponse
    merchant_metadata: MerchantMetadataResponse
