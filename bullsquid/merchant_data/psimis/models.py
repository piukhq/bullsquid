"""PSIMI request & response models."""

from datetime import datetime
from uuid import UUID

from pydantic import UUID4, BaseModel, validator

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.models import Slug
from bullsquid.merchant_data.validators import (
    nullify_blank_strings,
    string_must_not_be_blank,
)


class PSIMIMetadata(BaseModel):
    """Request/response model for PSIMI metadata."""

    value: str
    payment_scheme_merchant_name: str | None
    payment_scheme_slug: Slug

    _ = validator("value", allow_reuse=True)(string_must_not_be_blank)
    _ = validator("payment_scheme_merchant_name", allow_reuse=True)(
        nullify_blank_strings
    )


class CreatePSIMIRequest(BaseModel):
    """Request model for creating a PSIMI."""

    onboard: bool
    psimi_metadata: PSIMIMetadata


class PSIMIResponse(BaseModel):
    """PSIMI response model."""

    psimi_ref: UUID4
    psimi_metadata: PSIMIMetadata
    psimi_status: ResourceStatus
    date_added: datetime
    txm_status: TXMStatus = TXMStatus.NOT_ONBOARDED


class PSIMIRefsRequest(BaseModel):
    """Request model for deletion of PSIMIs."""

    psimi_refs: list[UUID4]
    reason: str | None

    _ = validator("reason", allow_reuse=True)(nullify_blank_strings)


class PSIMIDeletionResponse(BaseModel):
    """Response model for a deleted PSIMI."""

    psimi_ref: UUID
    status: ResourceStatus
    reason: str | None

    _ = validator("reason", allow_reuse=True)(nullify_blank_strings)
