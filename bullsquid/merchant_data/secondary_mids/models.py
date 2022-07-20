"""SecondaryMID request & response models."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, validator
from pydantic.types import UUID4

from bullsquid.merchant_data.enums import (
    PaymentEnrolmentStatus,
    ResourceStatus,
    TXMStatus,
)
from bullsquid.merchant_data.validators import nullify_blank_strings, string_must_not_be_blank


class SecondaryMIDMetadata(BaseModel):
    """Secondary MID metadata model."""

    payment_scheme_code: int
    secondary_mid: str
    payment_scheme_store_name: str | None
    payment_enrolment_status: PaymentEnrolmentStatus = PaymentEnrolmentStatus.UNKNOWN

    _ = validator("secondary_mid", allow_reuse=True)(
        string_must_not_be_blank
    )
    _ = validator("payment_scheme_store_name", allow_reuse=True)(
        nullify_blank_strings
    )


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


class SecondaryMIDDeletionResponse(BaseModel):
    """Response model for a deleted secondary MID."""

    secondary_mid_ref: UUID
    status: ResourceStatus


class SecondaryMIDDeletionListResponse(BaseModel):
    """Response model for a list of deleted secondary MIDs."""

    secondary_mids: list[SecondaryMIDDeletionResponse]
