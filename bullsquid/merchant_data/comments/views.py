"""
View functions for endpoints in the comments module.
"""
from uuid import UUID

from fastapi import Depends, Query, status
from fastapi.routing import APIRouter

from bullsquid.api.auth import JWTCredentials
from bullsquid.api.errors import ResourceNotFoundError
from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.auth import AccessLevel, require_access_level
from bullsquid.merchant_data.comments import db
from bullsquid.merchant_data.comments.models import (
    CommentResponse,
    CreateCommentRequest,
    EditCommentRequest,
    ListCommentsResponse,
)
from bullsquid.merchant_data.comments.tables import Comment
from bullsquid.merchant_data.enums import FilterSubjectType

router = APIRouter(prefix="/directory_comments")


@router.get("", response_model=ListCommentsResponse)
async def list_comments(
    ref: UUID = Query(),
    subject_type: FilterSubjectType | None = Query(default=None),
    n: int = Query(default=10),
    p: int = Query(default=1),
    _credentials: dict = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> ListCommentsResponse:
    """
    List comments by owner or subject ref.
    """

    entity_comments = await db.list_comments_by_subject(ref, n=n, p=p)
    lower_comments = await db.list_comments_by_owner(
        ref, filter_subject_type=subject_type, n=n, p=p
    )
    return ListCommentsResponse(
        entity_comments=entity_comments,
        lower_comments=lower_comments,
    )


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


@router.patch(
    "/{comment_ref}",
    response_model=CommentResponse,
)
async def edit_comment(
    comment_data: EditCommentRequest,
    comment_ref: UUID,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> CommentResponse:
    """
    Create response for editing a comment
    """
    try:
        comment = await db.edit_comment(
            comment_ref,
            comment_data,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return comment


@router.delete(
    "/{comment_ref}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    comment_ref: UUID,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE_DELETE)
    ),
) -> None:
    """Delete a comment."""
    try:
        await db.delete_comment(comment_ref)
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex
