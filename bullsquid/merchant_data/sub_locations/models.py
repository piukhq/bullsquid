"""Request & response model definitions for location endpoints."""
from pydantic import UUID4, validator

from bullsquid.merchant_data.locations_common.models import (
    LocationOverviewBase,
    LocationOverviewMetadataBase,
)
from bullsquid.merchant_data.models import BaseModel
from bullsquid.merchant_data.validators import nullify_blank_strings


class SubLocationDetailMetadata(LocationOverviewMetadataBase):
    """
    Detailed sub-location metadata request & response model.
    This is a superset of the sub-location overview metadata model.
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


class SubLocationDetails(LocationOverviewBase):
    """
    Response model for the `sub_location` object of a sub-location detail response.
    """

    location_metadata: SubLocationDetailMetadata
    linked_mids_count: int
    linked_secondary_mids_count: int


class ParentLocation(BaseModel):
    """Sub-Location parent info model."""

    location_ref: UUID4
    location_title: str


class SubLocationDetailResponse(BaseModel):
    """Response model for Sub-Location details."""

    parent_location: ParentLocation
    sub_location: SubLocationDetails
