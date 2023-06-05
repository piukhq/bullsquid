"""Request & response model definitions for merchant endpoints."""
import string
from datetime import datetime

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

    payment_scheme_slug: str
    mid: str
    visa_bin: str | None
    payment_enrolment_status = PaymentEnrolmentStatus.UNKNOWN

    @validator("visa_bin")
    @classmethod
    def visa_bin_must_be_numeric(cls, value: str | None) -> str | None:
        """Validate that visa_bin consists soley of digits from 0-9."""
        if value is not None and any(c not in string.digits for c in value):
            raise ValueError("visa_bin must be numeric")

        return value

    _ = validator(
        "payment_scheme_slug",
        "mid",
        "payment_enrolment_status",
        allow_reuse=True,
    )(string_must_not_be_blank)
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


class PrimaryMIDOverviewResponse(BaseModel):
    """Primary MID response model"""

    mid_ref: UUID4
    mid_metadata: PrimaryMIDMetadata
    mid_status: ResourceStatus
    date_added: datetime
    txm_status: TXMStatus = TXMStatus.NOT_ONBOARDED

    _ = validator("txm_status", allow_reuse=True)(string_must_not_be_blank)


class PrimaryMIDRefsRequest(BaseModel):
    """Request model for a deletion of primary MIDs."""

    mid_refs: list[UUID4]


class PrimaryMIDDeletionResponse(BaseModel):
    """Response model for a deletion of a primary MID."""

    mid_ref: UUID4
    mid_status: ResourceStatus


class LocationLinkRequest(BaseModel):
    """Request model for linking a location to a primary mid."""

    location_ref: UUID4


class LocationLinkResponse(BaseModel):
    """Response model for linking a location to a primary mid."""

    location_ref: UUID4
    location_title: str


class PrimaryMIDDetailResponse(BaseModel):
    """Detailed primary MID response model."""

    mid: PrimaryMIDOverviewResponse
    location: LocationLinkResponse | None


class UpdatePrimaryMIDs(BaseModel):
    """Request model for updating a number of primary MIDs enrolment status"""

    mid_refs: list[UUID4]
    payment_enrolment_status: PaymentEnrolmentStatus
