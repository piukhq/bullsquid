"""Identifier request & response models."""
from uuid import UUID

from pydantic import BaseModel

from bullsquid.merchant_data.enums import ResourceStatus


class IdentifierDeletionResponse(BaseModel):
    """Response model for a deleted identifier."""

    identifier_ref: UUID
    status: ResourceStatus


class IdentifierDeletionListResponse(BaseModel):
    """Response model for a list of deleted identifiers."""

    identifiers: list[IdentifierDeletionResponse]
