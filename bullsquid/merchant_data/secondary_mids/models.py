"""SecondaryMID request & response models."""
from datetime import datetime

from pydantic import BaseModel, validator
from pydantic.types import UUID4

from bullsquid.merchant_data.enums import (
    PaymentEnrolmentStatus,
    ResourceStatus,
    TXMStatus,
)
from bullsquid.merchant_data.models import Slug
from bullsquid.merchant_data.validators import (
    nullify_blank_strings,
    string_must_not_be_blank,
)


class SecondaryMIDMetadata(BaseModel):
    """Secondary MID metadata model."""

    payment_scheme_slug: Slug
    secondary_mid: str
    payment_scheme_store_name: str | None
    payment_enrolment_status: PaymentEnrolmentStatus = PaymentEnrolmentStatus.UNKNOWN

    _ = validator("payment_scheme_slug", "secondary_mid", allow_reuse=True)(
        string_must_not_be_blank
    )
    _ = validator("payment_scheme_store_name", allow_reuse=True)(nullify_blank_strings)


class CreateSecondaryMIDRequest(BaseModel):
    """Request model for creating a secondary MID."""

    onboard: bool
    secondary_mid_metadata: SecondaryMIDMetadata


class SecondaryMIDResponse(BaseModel):
    """Secondary MID response model."""

    secondary_mid_ref: UUID4
    secondary_mid_metadata: SecondaryMIDMetadata
    secondary_mid_status: ResourceStatus
    date_added: datetime
    txm_status: TXMStatus = TXMStatus.NOT_ONBOARDED


class SecondaryMIDRefsRequest(BaseModel):
    """Request model for deleting secondary MIDs."""

    secondary_mid_refs: list[UUID4]


class SecondaryMIDDeletionResponse(BaseModel):
    """Response model for a deleted secondary MID."""

    secondary_mid_ref: UUID4
    status: ResourceStatus


class LocationLinkRequest(BaseModel):
    """Request model for linking a secondary MID with a location."""

    location_refs: list[UUID4]


class LocationLinkResponse(BaseModel):
    """Response model for linking a secondary MID with a location."""

    link_ref: UUID4
    location_ref: UUID4
    location_title: str


class AssociatedLocationResponse(BaseModel):
    """Response model for listing locations associated to a secondary MID"""

    link_ref: UUID4
    location_ref: UUID4
    location_title: str


class UpdateSecondaryMIDRequest(BaseModel):
    """Request model for updating a secondary MID."""

    payment_scheme_store_name: str | None
    payment_enrolment_status: PaymentEnrolmentStatus | None

    _ = validator("payment_scheme_store_name", allow_reuse=True)(nullify_blank_strings)


class UpdateSecondaryMIDs(BaseModel):
    """Request model for updating a number of secondary MIDs enrolment status"""

    secondary_mid_refs: list[UUID4]
    payment_enrolment_status: PaymentEnrolmentStatus
