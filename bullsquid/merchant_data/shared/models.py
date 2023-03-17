"""
Pydantic models that are used in multiple other models modules.
Keeping them here avoids circular imports.
"""
from pydantic import UUID4, validator

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.models import BaseModel
from bullsquid.merchant_data.validators import (
    FlexibleUrl,
    nullify_blank_strings,
    string_must_not_be_blank,
)


class PlanMetadataResponse(BaseModel):
    """Plan details."""

    name: str
    plan_id: int | None
    slug: str | None
    icon_url: FlexibleUrl | None

    _ = validator("name", allow_reuse=True)(string_must_not_be_blank)
    _ = validator("slug", allow_reuse=True)(nullify_blank_strings)


class MerchantMetadataResponse(BaseModel):
    """Merchant details response model."""

    name: str
    icon_url: FlexibleUrl | None
    location_label: str

    _ = validator("name", "location_label", allow_reuse=True)(string_must_not_be_blank)


class MerchantPaymentSchemeCountResponse(BaseModel):
    """Counts of MIDs by payment scheme on a merchant."""

    slug: str
    mids: int
    secondary_mids: int
    psimis: int

    _ = validator("slug", allow_reuse=True)(string_must_not_be_blank)


class MerchantCountsResponse(BaseModel):
    """Counts of merchants, locations, and MIDs on a merchant."""

    locations: int
    sub_locations: int
    total_locations: int
    payment_schemes: list[MerchantPaymentSchemeCountResponse]


class MerchantOverviewResponse(BaseModel):
    """Merchant response model."""

    merchant_ref: UUID4
    merchant_status: ResourceStatus
    merchant_metadata: MerchantMetadataResponse
    merchant_counts: MerchantCountsResponse
