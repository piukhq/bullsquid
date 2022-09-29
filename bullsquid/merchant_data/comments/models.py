"""
Request & response models for the comments module.
"""
from datetime import datetime

from pydantic import UUID4, BaseModel, validator

from bullsquid.merchant_data.enums import ResourceType
from bullsquid.merchant_data.validators import (
    nullify_blank_strings,
    string_must_not_be_blank,
)


class CommentMetadata(BaseModel):
    """
    Request & response model for comment metadata.
    """

    comment_owner: UUID4
    owner_type: ResourceType
    text: str

    _ = validator("text", allow_reuse=True)(string_must_not_be_blank)

    @validator("owner_type")
    @classmethod
    def only_plan_or_merchant(cls, v: ResourceType) -> ResourceType:
        """
        Ensure that owner_type is either plan or merchant.
        Comments cannot be owned by any other kind of resource.
        """
        if v not in (ResourceType.PLAN, ResourceType.MERCHANT):
            raise ValueError("owner_type must be plan or merchant")
        return v


class CreateCommentRequest(BaseModel):
    """
    Request model for creating a comment.
    """

    metadata: CommentMetadata
    subjects: list[UUID4]
    subject_type: ResourceType


class CommentSubject(BaseModel):
    """
    Response model for the subject of a comment.
    """

    display_text: str
    plan_ref: UUID4
    merchant_ref: UUID4 | None
    subject_type: ResourceType
    entity_ref: UUID4
    icon_slug: str | None

    _ = validator("display_text", allow_reuse=True)(string_must_not_be_blank)
    _ = validator("icon_slug", allow_reuse=True)(nullify_blank_strings)


class CommentResponse(BaseModel):
    """
    Response model for a comment.
    """

    comment_ref: UUID4
    created_at: datetime
    created_by: str
    is_edited: bool
    is_deleted: bool
    subjects: list[CommentSubject]
    metadata: CommentMetadata
    responses: list["CommentResponse"]

    _ = validator("created_by", allow_reuse=True)(string_must_not_be_blank)
