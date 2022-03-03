"""Defines pydantic models used to translate between the database and the API."""
from pydantic import UUID4, BaseModel, HttpUrl, validator

from bullsquid.mids.tables import Merchant, PaymentScheme


class MerchantIn(BaseModel):
    """Client->Server model for a merchant."""

    name: str
    icon_url: HttpUrl | None
    slug: str | None
    payment_schemes: list[str]
    plan_id: int | None
    location_label: str

    @validator("name")
    @classmethod
    def name_must_be_unique(cls, name: str) -> str:
        """Ensures the merchant name is unique."""
        if Merchant.exists().where(Merchant.name == name).run_sync():
            raise ValueError("Merchant name must be unique.")
        return name

    @validator("slug")
    @classmethod
    def slug_must_be_unique(cls, slug: str) -> str:
        """Ensures the merchant slug is unique"""
        if Merchant.exists().where(Merchant.slug == slug).run_sync():
            raise ValueError("Merchant slug must be unique.")
        return slug

    @validator("payment_schemes")
    @classmethod
    def payment_schemes_must_exist(cls, slugs: list[str]) -> list[str]:
        """Ensures the given payment schemes exist."""
        payment_schemes = (
            PaymentScheme.objects().where(PaymentScheme.slug.is_in(slugs)).run_sync()
        )

        if len(payment_schemes) != len(slugs):
            missing = set(slugs) - {p.slug for p in payment_schemes}
            raise ValueError(
                f"The following payment schemes do not exist: {', '.join(missing)}"
            )

        return slugs


class MerchantOut(BaseModel):
    """Server->Client model for a merchant."""

    pk: UUID4
    name: str
    icon_url: HttpUrl | None
    slug: str | None
    payment_schemes: list[str]
    plan_id: int | None
    location_label: str
