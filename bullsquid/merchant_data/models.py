"""Defines pydantic models used to translate between the database and the API."""
from pydantic import UUID4, BaseModel, HttpUrl


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

    pk: UUID4
