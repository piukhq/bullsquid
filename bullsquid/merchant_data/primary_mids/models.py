"""Request & response model definitions for merchant endpoints."""


from datetime import datetime
from uuid import UUID

from pydantic import UUID4, validator

from bullsquid.merchant_data.enums import (
    PaymentEnrolmentStatus,
    ResourceStatus,
    TXMStatus,
)
from bullsquid.merchant_data.models import BaseModel
from bullsquid.merchant_data.validators import (
    nullify_blank_strings,
    string_must_not_be_blank,
)


class PrimaryMIDMetadata(BaseModel):
    """Primary MID metadata model."""

    payment_scheme_code: int
    mid: str
    visa_bin: str | None
    payment_enrolment_status: PaymentEnrolmentStatus = PaymentEnrolmentStatus.UNKNOWN

    _ = validator("mid", "payment_enrolment_status", allow_reuse=True)(
        string_must_not_be_blank
    )
    _ = validator("visa_bin", allow_reuse=True)(nullify_blank_strings)


class CreatePrimaryMIDRequest(BaseModel):
    """Request model for creating a primary MID."""

    onboard: bool
    mid_metadata: PrimaryMIDMetadata


class UpdatePrimaryMIDRequest(BaseModel):
    """Request model for updating a primary MID."""

    payment_enrolment_status: PaymentEnrolmentStatus | None
    visa_bin: str | None

    _ = validator("visa_bin", allow_reuse=True)(nullify_blank_strings)


class PrimaryMIDResponse(BaseModel):
    """Primary MID response model"""

    mid_ref: UUID4
    mid_metadata: PrimaryMIDMetadata
    mid_status: ResourceStatus
    date_added: datetime
    txm_status: TXMStatus = TXMStatus.NOT_ONBOARDED

    _ = validator("txm_status", allow_reuse=True)(string_must_not_be_blank)


class PrimaryMIDDeletionResponse(BaseModel):
    """Response model for a deletion of a primary MID."""

    mid_ref: UUID
    mid_status: ResourceStatus


class PrimaryMIDDeletionListResponse(BaseModel):
    """Response model for the deletion of primary MIDs."""

    mids: list[PrimaryMIDDeletionResponse]
