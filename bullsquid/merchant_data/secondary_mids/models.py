"""SecondaryMID request & response models."""
from uuid import UUID

from pydantic import BaseModel

from bullsquid.merchant_data.enums import ResourceStatus


class SecondaryMIDDeletionResponse(BaseModel):
    """Response model for a deleted secondary MID."""

    secondary_mid_ref: UUID
    status: ResourceStatus


class SecondaryMIDDeletionListResponse(BaseModel):
    """Response model for a list of deleted secondary MIDs."""

    secondary_mids: list[SecondaryMIDDeletionResponse]
