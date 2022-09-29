"""
View functions for endpoints in the comments module.
"""
from fastapi import status
from fastapi.routing import APIRouter

from bullsquid.api.errors import ResourceNotFoundError
from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.comments import db
from bullsquid.merchant_data.comments.models import (
    CommentResponse,
    CreateCommentRequest,
)

router = APIRouter(prefix="/directory_comments")


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(comment_data: CreateCommentRequest) -> CommentResponse:
    """
    Create and return a comment on a subject.
    """
    try:
        comment = await db.create_comment(comment_data)
    except NoSuchRecord as ex:
        # TODO: we can't yet distinguish between body.metadata.comment_owner and body.subjects
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["body"]) from ex

    return comment
