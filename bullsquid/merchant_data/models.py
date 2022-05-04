"""Defines pydantic models used to translate between the database and the API."""
from pydantic import UUID4
from pydantic import BaseModel as PydanticBaseModel
from pydantic import HttpUrl, root_validator, validator


class BaseModel(PydanticBaseModel):
    """Custom Pydantic model base class."""

    class Config:
        """
        Global pydantic model configuration options go here.
        https://pydantic-docs.helpmanual.io/usage/model_config/#options
        """

        # perform validation even on omitted fields
        validate_all = True


def alias_pk(field_name: str):  # type: ignore
    """Returns a root validator that renames "pk" to the given field name."""

    def validator(_: BaseModel, values: dict) -> dict:
        values[field_name] = values.pop("pk")
        return values

    return root_validator(pre=True, allow_reuse=True)(validator)


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

    plan_ref: UUID4
    status: str

    _alias_pk = alias_pk("plan_ref")


class Merchant(BaseModel):
    """Merchant request model."""

    name: str
    icon_url: HttpUrl | None
    location_label: str


class MerchantWithPK(Merchant):
    """Merchant response model with a primary key."""

    merchant_ref: UUID4
    status: str

    _alias_pk = alias_pk("merchant_ref")


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

    location_ref: UUID4

    _alias_pk = alias_pk("location_ref")
