"""Request & response model definitions for location endpoints."""
from pydantic import UUID4, validator

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.locations_common.models import (
    LocationOverviewBase,
    LocationOverviewMetadataBase,
    SubLocationOverviewResponse,
)
from bullsquid.merchant_data.models import BaseModel
from bullsquid.merchant_data.primary_mids.models import LocationLinkResponse
from bullsquid.merchant_data.validators import (
    nullify_blank_strings,
    string_must_not_be_blank,
)


class LocationOverviewMetadata(LocationOverviewMetadataBase):
    """Location details - adds location_id to the general base model."""

    location_id: str

    _ = validator("location_id", allow_reuse=True)(string_must_not_be_blank)


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


class LocationOverviewResponse(LocationOverviewBase):
    """Location overview response model."""

    location_metadata: LocationOverviewMetadata
    sub_locations: list[SubLocationOverviewResponse] | None


class LocationDetailResponse(LocationOverviewBase):
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


class AvailablePrimaryMID(BaseModel):
    """Response model for Populate Available MIDs endpoint"""

    location_link: LocationLinkResponse | None
    mid: PrimaryMIDLinkResponse
