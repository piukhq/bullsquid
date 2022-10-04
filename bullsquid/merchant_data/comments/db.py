"""
Database access functions for the comments module.
"""
from typing import Type, TypeVar, cast
from uuid import UUID

from piccolo.columns import Column
from piccolo.table import Table

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.comments.models import (
    CommentMetadata,
    CommentResponse,
    CommentSubject,
    CreateCommentRequest,
)
from bullsquid.merchant_data.comments.tables import Comment
from bullsquid.merchant_data.db import RESOURCE_TYPE_TO_TABLE
from bullsquid.merchant_data.enums import ResourceType
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.db import get_plan
from bullsquid.merchant_data.plans.tables import Plan

T = TypeVar("T", bound=Table)


async def find_subjects(table: Type[T], entity_refs: list[UUID]) -> list[T]:
    """
    Query the given table for all entities in the entity_refs list.
    """
    # clearly this function can only be called on tables with a pk field.
    pk: Column = table.pk  # type: ignore
    return await table.objects().where(pk.is_in(entity_refs))


def get_subject_merchant_ref(subject: Table) -> UUID | None:
    """
    Returns the associated merchant ref for the given subject.
    If the subjet is a plan, then None is returned instead.
    """
    match subject.__class__.__qualname__:
        case Plan.__qualname__:
            return None
        case Merchant.__qualname__:
            return cast(Merchant, subject).pk

    # we cast to Location for mypy's benefit. this can actually be any type with
    # a `merchant` field on it, i.e. Location, PrimaryMID, SecondaryMID, or
    # PSIMI.
    return cast(Location, subject).merchant


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

    plan: UUID
    if comment_data.metadata.owner_type == ResourceType.PLAN:
        plan = (await get_plan(comment_data.metadata.comment_owner)).pk
    elif comment_data.metadata.owner_type == ResourceType.MERCHANT:
        plan = (
            await get_merchant(
                comment_data.metadata.comment_owner, plan_ref=None, validate_plan=False
            )
        ).plan

    comment = Comment(
        text=comment_data.metadata.text,
        owner=comment_data.metadata.comment_owner,
        owner_type=comment_data.metadata.owner_type,
        subjects=comment_data.subjects,
        subject_type=comment_data.subject_type,
        parent=parent,
        created_by="somebody",
    )
    await comment.save()

    subjects = await find_subjects(
        RESOURCE_TYPE_TO_TABLE[ResourceType(comment.subject_type)], comment.subjects
    )

    return CommentResponse(
        comment_ref=comment.pk,
        created_at=comment.created_at,
        created_by=comment.created_by,
        is_edited=comment.is_edited,
        is_deleted=comment.is_deleted,
        subjects=[
            CommentSubject(
                display_text="string",
                plan_ref=plan,
                merchant_ref=get_subject_merchant_ref(subject),
                subject_type=comment.subject_type,
                entity_ref=cast(Plan, subject).pk,  # cast only for mypy's benefit
                icon_slug=None,
            )
            for subject in subjects
        ],
        metadata=CommentMetadata(
            comment_owner=comment.owner,
            owner_type=comment.owner_type,
            text=comment.text,
        ),
        responses=[],
    )
