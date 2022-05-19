"""Request & response model definitions for merchant endpoints."""
from pydantic import UUID4, HttpUrl, validator

from bullsquid.merchant_data.models import BaseModel
from bullsquid.merchant_data.validators import string_must_not_be_blank


class CreateMerchantRequest(BaseModel):
    """Merchant request model."""

    name: str
    icon_url: HttpUrl | None
    location_label: str

    _ = validator("name", "location_label", allow_reuse=True)(string_must_not_be_blank)


class MerchantMetadataResponse(BaseModel):
    """Merchant details response model."""

    name: str
    icon_url: HttpUrl | None
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


class MerchantResponse(BaseModel):
    """Merchant response model."""

    merchant_ref: UUID4
    merchant_status: str
    merchant_metadata: MerchantMetadataResponse
    merchant_counts: MerchantCountsResponse

    _ = validator("merchant_status", allow_reuse=True)(string_must_not_be_blank)
