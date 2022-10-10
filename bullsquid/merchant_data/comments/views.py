"""
View functions for endpoints in the comments module.
"""
from uuid import UUID

from fastapi import Depends, status
from fastapi.routing import APIRouter

from bullsquid.api.auth import JWTCredentials
from bullsquid.api.errors import ResourceNotFoundError
from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.auth import AccessLevel, require_access_level
from bullsquid.merchant_data.comments import db
from bullsquid.merchant_data.comments.models import (
    CommentResponse,
    CreateCommentRequest,
)
from bullsquid.merchant_data.comments.tables import Comment

router = APIRouter(prefix="/directory_comments")


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment_data: CreateCommentRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> CommentResponse:
    """
    Create and return a comment on a subject.
    """
    try:
        comment = await db.create_comment(comment_data, parent=None)
    except NoSuchRecord as ex:
        # TODO: we can't yet distinguish between body.metadata.comment_owner and body.subjects
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["body"]) from ex

    return comment


@router.post(
    "/{comment_ref}",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment_reply(
    comment_data: CreateCommentRequest,
    comment_ref: UUID,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> CommentResponse:
    """
    Create and return a response to a top level comment
    """
    try:
        comment = await db.create_comment(comment_data, parent=comment_ref)
    except NoSuchRecord as ex:
        loc = ["path"] if ex.table == Comment else ["body"]
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc) from ex

    return comment
