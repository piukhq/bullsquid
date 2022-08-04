"""Request & response model definitions for location endpoints."""
from datetime import datetime

from pydantic import UUID4, validator

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.models import BaseModel
from bullsquid.merchant_data.validators import (
    nullify_blank_strings,
    string_must_not_be_blank,
)


class LocationMetadataResponse(BaseModel):
    """Location details."""

    name: str | None
    location_id: str
    merchant_internal_id: str | None
    is_physical_location: bool
    address_line_1: str | None
    town_city: str | None
    postcode: str | None

    _ = validator("location_id", allow_reuse=True)(string_must_not_be_blank)
    _ = validator(
        "name",
        "merchant_internal_id",
        "address_line_1",
        "town_city",
        "postcode",
        allow_reuse=True,
    )(nullify_blank_strings)


class LocationPaymentSchemeCountResponse(BaseModel):
    """Counts of MIDs by payment scheme on a location."""

    label: str
    scheme_code: int
    count: int

    _ = validator("label", allow_reuse=True)(string_must_not_be_blank)


class LocationOverviewResponse(BaseModel):
    """Location response model."""

    location_ref: UUID4
    location_status: ResourceStatus
    location_metadata: LocationMetadataResponse
    payment_schemes: list[LocationPaymentSchemeCountResponse]
    date_added: datetime
