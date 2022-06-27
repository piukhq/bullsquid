"""Identifier request & response models."""
from datetime import datetime
from uuid import UUID

from pydantic import UUID4, BaseModel, validator

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.validators import string_must_not_be_blank


class IdentifierMetadata(BaseModel):
    """Request/response model for identifier metadata."""

    value: str
    payment_scheme_merchant_name: str
    payment_scheme_code: int

    _ = validator("value", "payment_scheme_merchant_name", allow_reuse=True)(
        string_must_not_be_blank
    )


class CreateIdentifierRequest(BaseModel):
    """Request model for creating an identifier."""

    onboard: bool
    identifier_metadata: IdentifierMetadata


class IdentifierResponse(BaseModel):
    """Identifier response model."""

    identifier_ref: UUID4
    identifier_metadata: IdentifierMetadata
    identifier_status: ResourceStatus
    date_added: datetime


class IdentifierDeletionResponse(BaseModel):
    """Response model for a deleted identifier."""

    identifier_ref: UUID
    status: ResourceStatus


class IdentifierDeletionListResponse(BaseModel):
    """Response model for a list of deleted identifiers."""

    identifiers: list[IdentifierDeletionResponse]
