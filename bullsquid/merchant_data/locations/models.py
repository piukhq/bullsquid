"""Request & response model definitions for location endpoints."""
from datetime import datetime

from pydantic import UUID4, root_validator, validator

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.models import BaseModel
from bullsquid.merchant_data.validators import (
    nullify_blank_strings,
    string_must_not_be_blank,
)


class LocationOverviewMetadata(BaseModel):
    """Location details."""

    name: str
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

    @root_validator
    @classmethod
    def physical_locations_must_have_addresses(cls, values: dict) -> dict:
        """
        Validate that if is_physical_location has been set to true, the location
        has a minimum of an address_line_1 and postcode present.
        """
        if values.get("is_physical_location"):
            address = [values.get("address_line_1"), values.get("postcode")]
            if not all(address):
                raise ValueError(
                    "address_line_1 and postcode must be provided when is_physical_location is true"
                )
        return values


class LocationDetailMetadata(LocationOverviewMetadata):
    """
    Detailed location metadata request & response model.
    This is a superset of the location overview metadata model.
    """

    address_line_2: str | None
    county: str | None
    country: str | None

    _ = validator(
        "address_line_2",
        "county",
        "country",
        allow_reuse=True,
    )(nullify_blank_strings)


class LocationPaymentSchemeCountResponse(BaseModel):
    """Counts of MIDs by payment scheme on a location."""

    label: str
    scheme_code: int
    count: int

    _ = validator("label", allow_reuse=True)(string_must_not_be_blank)


class LocationOverviewResponse(BaseModel):
    """Location overview response model."""

    location_ref: UUID4
    location_status: ResourceStatus
    location_metadata: LocationOverviewMetadata
    payment_schemes: list[LocationPaymentSchemeCountResponse]
    date_added: datetime


class LocationDetailResponse(LocationOverviewResponse):
    """Location detail response model"""

    location_metadata: LocationDetailMetadata
    linked_mids_count: int
    linked_secondary_mids_count: int


class LocationDeletionRequest(BaseModel):
    """Request model for deleting locations."""

    location_refs: list[UUID4]


class LocationDeletionResponse(BaseModel):
    """Response model for deleting locations."""

    location_ref: UUID4
    location_status: ResourceStatus


class PrimaryMIDLinkRequest(BaseModel):
    """Request model for linking a primary MID with a location."""

    mid_refs: list[UUID4]


class PrimaryMIDLinkResponse(BaseModel):
    """Request model for linking a primary MID with a location."""

    mid_ref: UUID4
    payment_scheme_slug: str
    mid_value: str


class SecondaryMIDLinkRequest(BaseModel):
    """Request model for linking a location with a secondary MID."""

    secondary_mid_refs: list[UUID4]


class SecondaryMIDLinkResponse(BaseModel):
    """Response model for linking a location with a secondary MID."""

    link_ref: UUID4
    secondary_mid_ref: UUID4
    payment_scheme_slug: str
    secondary_mid_value: str
