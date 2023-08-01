"""Request & response model definitions for location endpoints."""
from pydantic import UUID4, root_validator, validator

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


class ParentLocation(BaseModel):
    """Sub-Location parent info model."""

    location_ref: UUID4
    location_title: str


class SubLocationDetailResponse(BaseModel):
    """Response model for Sub-Location details."""

    parent_location: ParentLocation
    sub_location: SubLocationDetails


class SubLocationReparentRequest(BaseModel):
    """Request model for reparenting a sub-location."""

    parent_ref: UUID4 | None
    location_id: str | None

    @root_validator
    @classmethod
    def sub_locations_must_have_location_id(cls, values: dict) -> dict:
        """
        Validate that sub_location is either populated with parent_ref or location_id

        """
        if values.get("parent_ref") is values.get("location_id") is None:
            raise ValueError("Either parent_ref or location_id must be provided")
        return values

    _ = validator("location_id", allow_reuse=True)(nullify_blank_strings)


class SubLocationReparentResponse(BaseModel):
    """Response model for reparenting a sub-location."""

    location_ref: UUID4
    parent_ref: UUID4 | None
