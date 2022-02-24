"""Defines pydantic models used to translate between the database and the API."""
from pydantic import UUID4, BaseModel, HttpUrl


class MerchantIn(BaseModel):
    """Represents a merchant such as Iceland or Wasabi."""

    name: str
    icon_url: HttpUrl | None
    slug: str | None
    payment_schemes: list[str]
    plan_id: int | None
    location_label: str


class MerchantOut(BaseModel):
    """Represents a merchant such as Iceland or Wasabi."""

    pk: UUID4
    name: str
    icon_url: HttpUrl | None
    slug: str | None
    payment_schemes: list[str]
    plan_id: int | None
    location_label: str
