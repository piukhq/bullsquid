"""Defines pydantic models used to translate between the database and the API."""
from pydantic import UUID4
from pydantic import BaseModel as PydanticBaseModel
from pydantic import HttpUrl, validator


def string_must_not_be_blank(value: str | None) -> str | None:
    """
    Validate that the provided string field is not blank.
    """
    if value is not None and not value.strip():
        raise ValueError("must not be blank if not null")

    return value


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

    _ = validator("name", "slug", allow_reuse=True)(string_must_not_be_blank)


class PlanMetadata(BaseModel):
    """Plan details."""

    name: str
    plan_id: int | None
    slug: str | None
    icon_url: HttpUrl | None

    _ = validator("name", "slug", allow_reuse=True)(string_must_not_be_blank)


class PlanPaymentSchemeCount(BaseModel):
    """Counts of MIDs by payment scheme on a plan."""

    label: str
    scheme_code: int
    count: int

    _ = validator("label", allow_reuse=True)(string_must_not_be_blank)


class PlanCounts(BaseModel):
    """Counts of merchants, locations, and MIDs on a plan."""

    merchants: int
    locations: int
    payment_schemes: list[PlanPaymentSchemeCount]


class PlanResponse(BaseModel):
    """Plan response model."""

    plan_ref: UUID4
    plan_status: str
    plan_metadata: PlanMetadata
    plan_counts: PlanCounts

    _ = validator("plan_status", allow_reuse=True)(string_must_not_be_blank)


class Merchant(BaseModel):
    """Merchant request model."""

    name: str
    icon_url: HttpUrl | None
    location_label: str

    _ = validator("name", "location_label", allow_reuse=True)(string_must_not_be_blank)


class MerchantMetadata(BaseModel):
    """Merchant details."""

    name: str
    icon_url: HttpUrl | None
    location_label: str

    _ = validator("name", "location_label", allow_reuse=True)(string_must_not_be_blank)


class MerchantPaymentSchemeCount(BaseModel):
    """Counts of MIDs by payment scheme on a merchant."""

    label: str
    scheme_code: int
    count: int

    _ = validator("label", allow_reuse=True)(string_must_not_be_blank)


class MerchantCounts(BaseModel):
    """Counts of merchants, locations, and MIDs on a merchant."""

    merchants: int
    locations: int
    payment_schemes: list[MerchantPaymentSchemeCount]


class MerchantResponse(BaseModel):
    """Merchant response model."""

    merchant_ref: UUID4
    merchant_status: str
    merchant_metadata: MerchantMetadata
    merchant_counts: MerchantCounts

    _ = validator("merchant_status", allow_reuse=True)(string_must_not_be_blank)
