"""Defines pydantic models used to translate between the database and the API."""
from pydantic import UUID4
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, HttpUrl, validator


class BaseModel(PydanticBaseModel):
    """Custom Pydantic model base class."""

    class Config:
        """
        Global pydantic model configuration options go here.
        https://pydantic-docs.helpmanual.io/usage/model_config/#options
        """

        # perform validation even on omitted fields
        validate_all = True


class Plan(BaseModel):
    """Plan request model."""

    name: str
    icon_url: HttpUrl | None
    slug: str | None
    plan_id: int | None

    @validator("name", "slug")
    @classmethod
    def provided_strings_must_not_be_blank(cls, value: str | None) -> str | None:
        """
        Validate that the provided string fields are not blank.
        """
        if value is not None and not value.strip():
            raise ValueError("must not be blank if not null")

        return value


class PlanWithPK(Plan):
    """Plan response model with a primary key."""

    plan_ref: UUID4 = Field(alias="pk")
    status: str


class Merchant(BaseModel):
    """Merchant request model."""

    name: str
    icon_url: HttpUrl | None
    slug: str | None
    payment_schemes: list[str]
    plan_id: int | None
    location_label: str


class MerchantWithPK(Merchant):
    """Merchant response model with a primary key."""

    merchant_ref: UUID4 = Field(alias="pk")


class Location(BaseModel):
    """Location request model."""

    name: str
    location_id: str
    merchant_internal_id: str | None
    is_physical_location: bool
    address_line_1: str | None
    address_line_2: str | None
    town_city: str | None
    county: str | None
    country: str | None
    postcode: str | None

    @validator("address_line_1", "postcode")
    @classmethod
    def physical_location_fields_are_present(
        cls, v: str | None, values: dict
    ) -> str | None:
        """Validate that minimal address information is present on physical locations."""
        if values["is_physical_location"] and not v:
            raise ValueError("required for physical locations")

        return v


class LocationWithPK(Location):
    """Location response model with a primary key."""

    location_ref: UUID4 = Field(alias="pk")
