"""
Database access functions for the comments module.
"""
from collections import defaultdict
from typing import Type, TypeVar
from uuid import UUID

from piccolo.table import Table

from bullsquid.db import NoSuchRecord, paginate
from bullsquid.merchant_data.comments.models import (
    CommentMetadataResponse,
    CommentResponse,
    CommentSubject,
    CreateCommentRequest,
    EditCommentRequest,
    SubjectComments,
)
from bullsquid.merchant_data.comments.tables import Comment
from bullsquid.merchant_data.db import RESOURCE_TYPE_TO_TABLE, TableWithPK
from bullsquid.merchant_data.enums import FilterSubjectType, ResourceType
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID

T = TypeVar("T", bound=TableWithPK)


async def find_subjects(table: Type[T], entity_refs: list[UUID]) -> list[T]:
    """
    Query the given table for all entities in the entity_refs list.
    """
    # clearly this function can only be called on tables with a pk field.
    subjects = await table.objects().where(table.pk.is_in(entity_refs))
    if len(subjects) != len(entity_refs):
        raise NoSuchRecord(table)
    return subjects


def validate_subject_owners(
    subjects: list[TableWithPK], *, subject_type: ResourceType, owner: UUID
) -> None:
    """
    Raise a NoSuchRecord error if the given subjects do not match the given owner.
    """

    def plan_owner(subject: Table) -> bool:
        return isinstance(subject, Plan) and subject.pk == owner

    def merchant_owner(subject: Table) -> bool:
        return isinstance(subject, Merchant) and subject.plan == owner

    def other_owner(subject: Table) -> bool:
        return (
            isinstance(subject, Location | PrimaryMID | SecondaryMID | Identifier)
            and subject.merchant == owner
        )

    match subject_type:
        case ResourceType.PLAN:
            predicate = plan_owner
        case ResourceType.MERCHANT:
            predicate = merchant_owner
        case _:
            predicate = other_owner

    if not all(predicate(subject) for subject in subjects):
        raise NoSuchRecord(RESOURCE_TYPE_TO_TABLE[subject_type])


async def _list_comments_by_parent(parent: Comment) -> list[CommentResponse]:
    comments = await Comment.objects().where(Comment.parent == parent)

    return [
        await create_comment_response(
            comment,
            subjects=await find_subjects(
                RESOURCE_TYPE_TO_TABLE[ResourceType(parent.subject_type)],
                comment.subjects,
            ),
        )
        for comment in comments
    ]


async def create_comment_response(
    comment: Comment, *, subjects: list[TableWithPK]
) -> CommentResponse:
    """
    Create and return a CommentResponse instace for the given comment and list
    of subjects.
    """
    return CommentResponse(
        comment_ref=comment.pk,
        created_at=comment.created_at,
        created_by=comment.created_by,
        is_edited=comment.is_edited,
        is_deleted=comment.is_deleted,
        subjects=[
            CommentSubject(
                display_text=subject.display_text,
                subject_ref=subject.pk,
                icon_slug=None,
            )
            for subject in subjects
        ],
        metadata=CommentMetadataResponse(
            owner_ref=comment.owner,
            owner_type=comment.owner_type,
            text=None if comment.is_deleted is True else comment.text,
        ),
        responses=await _list_comments_by_parent(comment),
    )


async def list_comments_by_owner(
    ref: UUID, *, n: int, p: int, filter_subject_type: FilterSubjectType | None = None
) -> list[SubjectComments]:
    """
    List all comments with the given ref as their owner.
    Returns a list of SubjectComments instances.
    """

    # we exclude plan comments because they will already show up in the
    # query-by-subject part of the process.
    where = (
        (Comment.owner == ref)
        & (Comment.parent.is_null())
        & (Comment.subject_type != ResourceType.PLAN)
    )
    if filter_subject_type is not None:
        where &= Comment.subject_type == ResourceType(filter_subject_type.value)

    comments = await paginate(Comment.objects().where(where), n=n, p=p)

    comments_by_subject_type = defaultdict(list)
    for comment in comments:
        comments_by_subject_type[comment.subject_type].append(comment)

    # TODO: rewrite with list comprehensions once 3.11 is out.
    # at least as far as 3.10.8 you can't have an async comprehension inside a sync one.
    result = []
    for subject_type, comments in comments_by_subject_type.items():
        result.append(
            SubjectComments(
                subject_type=subject_type,
                comments=[
                    await create_comment_response(
                        comment,
                        subjects=await find_subjects(
                            RESOURCE_TYPE_TO_TABLE[ResourceType(comment.subject_type)],
                            entity_refs=comment.subjects,
                        ),
                    )
                    for comment in comments
                ],
            )
        )
    return result


async def list_comments_by_subject(
    ref: UUID, *, n: int, p: int
) -> SubjectComments | None:
    """
    List all comments with the given ref as one of their subjects.
    Returns a list of CommentResponse instances.
    """
    comments = await paginate(
        Comment.objects().where(Comment.subjects.any(ref), Comment.parent.is_null()),
        n=n,
        p=p,
    )

    return (
        SubjectComments(
            subject_type=comments[0].subject_type,
            comments=[
                await create_comment_response(
                    comment,
                    subjects=await find_subjects(
                        RESOURCE_TYPE_TO_TABLE[ResourceType(comment.subject_type)],
                        entity_refs=comment.subjects,
                    ),
                )
                for comment in comments
            ],
        )
        if comments
        else None
    )


async def create_comment(
    comment_data: CreateCommentRequest, parent: UUID | None
) -> CommentResponse:
    """
    Create a comment from the given request data.
    Returns a CommentResponse instance.
    """
    # fetch the related records and raise errors if they do not exist.
    if parent and not await Comment.exists().where(Comment.pk == parent):
        raise NoSuchRecord(Comment)

    # ensure the owner exists
    table = RESOURCE_TYPE_TO_TABLE[comment_data.metadata.owner_type]
    if not await table.exists().where(table.pk == comment_data.metadata.owner_ref):
        raise NoSuchRecord(table)

    # find & validated related subjects
    subjects = await find_subjects(
        RESOURCE_TYPE_TO_TABLE[comment_data.subject_type],
        comment_data.subjects,
    )
    validate_subject_owners(
        subjects,
        subject_type=comment_data.subject_type,
        owner=comment_data.metadata.owner_ref,
    )

    comment = Comment(
        text=comment_data.metadata.text,
        owner=comment_data.metadata.owner_ref,
        owner_type=comment_data.metadata.owner_type,
        subjects=comment_data.subjects,
        subject_type=comment_data.subject_type,
        parent=parent,
        created_by="somebody",
    )
    await comment.save()

    return await create_comment_response(comment, subjects=subjects)


async def edit_comment(
    comment_ref: UUID,
    fields: EditCommentRequest,
) -> CommentResponse:
    """Edit existing comment with new text"""
    comment = await Comment.objects().get(Comment.pk == comment_ref)

    if not comment:
        raise NoSuchRecord(Comment)

    subjects = await find_subjects(
        RESOURCE_TYPE_TO_TABLE[comment.subject_type],
        comment.subjects,
    )

    comment.text = fields.text
    comment.is_edited = True
    await comment.save()
    return await create_comment_response(comment, subjects=subjects)


async def delete_comment(
    comment_ref: UUID,
) -> None:
    """Delete a comment."""
    comment = await Comment.objects().get(Comment.pk == comment_ref)

    if not comment:
        raise NoSuchRecord(Comment)

    comment.is_deleted = True
    await comment.save()
