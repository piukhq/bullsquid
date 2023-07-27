"""
Models shared between locations and sub-locations.
"""
from datetime import datetime

from pydantic import UUID4, root_validator, validator

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.models import BaseModel
from bullsquid.merchant_data.validators import nullify_blank_strings


class LocationOverviewMetadataBase(BaseModel):
    """Location details."""

    name: str
    merchant_internal_id: str | None
    is_physical_location: bool
    address_line_1: str | None
    town_city: str | None
    postcode: str | None

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
                    "address_line_1 and postcode must be provided when "
                    "is_physical_location is true"
                )
        return values


class LocationOverviewBase(BaseModel):
    """Base location overview model."""

    location_ref: UUID4
    location_status: ResourceStatus
    date_added: datetime


class SubLocationOverviewResponse(LocationOverviewBase):
    """Sub-location overview response model."""

    location_metadata: LocationOverviewMetadataBase
