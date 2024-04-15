"""
Request & response models for the comments module.
"""

from datetime import datetime

from pydantic import UUID4, BaseModel, root_validator, validator

from bullsquid.merchant_data.enums import ResourceType
from bullsquid.merchant_data.models import Slug
from bullsquid.merchant_data.validators import (
    nullify_blank_strings,
    string_must_not_be_blank,
)


class CommentMetadataBase(BaseModel):
    """
    Request & response model for comment metadata.
    """

    owner_ref: UUID4
    owner_type: ResourceType

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


class CommentMetadataRequest(CommentMetadataBase):
    """
    Request model for editing and creating comment text
    """

    text: str

    _ = validator("text", allow_reuse=True)(string_must_not_be_blank)


class CommentMetadataResponse(CommentMetadataBase):
    """
    Response model for deleting comment text
    """

    text: str | None

    _ = validator("text", allow_reuse=True)(nullify_blank_strings)


class CreateCommentRequest(BaseModel):
    """
    Request model for creating a comment.
    """

    metadata: CommentMetadataRequest
    subjects: list[UUID4]
    subject_type: ResourceType

    @root_validator
    @classmethod
    def correct_subject_and_owner_types(cls, values: dict) -> dict:
        """
        Ensure that the given owner type matches the given subject type.
        """
        # no metadata means it failed validation, so no point checking this.
        if "metadata" not in values:
            return values

        owner_types = {
            ResourceType.PLAN: ResourceType.PLAN,
            ResourceType.MERCHANT: ResourceType.PLAN,
            ResourceType.LOCATION: ResourceType.MERCHANT,
            ResourceType.PRIMARY_MID: ResourceType.MERCHANT,
            ResourceType.SECONDARY_MID: ResourceType.MERCHANT,
            ResourceType.PSIMI: ResourceType.MERCHANT,
        }

        subject_type = ResourceType(values["subject_type"])
        actual = ResourceType(values["metadata"].owner_type)
        expected = owner_types[subject_type]
        if actual != expected:
            raise ValueError(
                f"a subject of type {subject_type} should have an owner type of "
                f"{expected}, but {actual} was passed instead."
            )

        return values


class CommentSubject(BaseModel):
    """
    Response model for the subject of a comment.
    """

    display_text: str
    subject_ref: UUID4
    icon_slug: Slug | None

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
    metadata: CommentMetadataResponse
    responses: list["CommentResponse"]

    _ = validator("created_by", allow_reuse=True)(string_must_not_be_blank)


class SubjectComments(BaseModel):
    """
    A group of comments with a common subject type.
    """

    subject_type: ResourceType
    comments: list[CommentResponse]


class ListCommentsResponse(BaseModel):
    """
    Response model for a list of entity and lower comments.
    """

    entity_comments: SubjectComments | None
    lower_comments: list[SubjectComments]


class EditCommentRequest(BaseModel):
    """
    Response model for editing the text in a comment
    """

    text: str

    _ = validator("text", allow_reuse=True)(string_must_not_be_blank)
