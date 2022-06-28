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
from bullsquid.merchant_data.validators import string_must_not_be_blank


class PrimaryMIDMetadata(BaseModel):
    """Primary MID metadata model."""

    payment_scheme_code: int
    mid: str
    visa_bin: str | None
    payment_enrolment_status: PaymentEnrolmentStatus = PaymentEnrolmentStatus.UNKNOWN

    _ = validator("mid", "visa_bin", "payment_enrolment_status", allow_reuse=True)(
        string_must_not_be_blank
    )


class CreatePrimaryMIDRequest(BaseModel):
    """Request model for creating a primary MID."""

    onboard: bool
    mid_metadata: PrimaryMIDMetadata


class PrimaryMIDResponse(BaseModel):
    """Primary MID response model"""

    mid_ref: UUID4
    mid_metadata: PrimaryMIDMetadata
    date_added: datetime
    txm_status: TXMStatus = TXMStatus.NOT_ONBOARDED

    _ = validator("txm_status", allow_reuse=True)(string_must_not_be_blank)


class PrimaryMIDListResponse(BaseModel):
    """Response model for a list of primary MIDs."""

    mids: list[PrimaryMIDResponse]


class PrimaryMIDDeletionResponse(BaseModel):
    """Response model for a deletion of a primary MID."""

    mid_ref: UUID
    status: ResourceStatus


class PrimaryMIDDeletionListResponse(BaseModel):
    """Response model for the deletion of primary MIDs."""

    mids: list[PrimaryMIDDeletionResponse]
