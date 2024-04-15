"""
Database table definitions for the comments module.
"""

from piccolo.columns import (
    UUID,
    Array,
    Boolean,
    ForeignKey,
    Text,
    Timestamptz,
    Selectable,
)
from piccolo.table import Table
from piccolo.query import Objects, Select

from bullsquid.merchant_data.enums import ResourceType


class Comment(Table):
    """
    Represents a comment on an entity or a set of entities.
    """

    pk = UUID(primary_key=True)
    text = Text(required=True)
    owner = UUID(required=True)
    owner_type = Text(choices=ResourceType, required=True)
    subjects = Array(UUID())
    subject_type = Text(choices=ResourceType, required=True)
    parent = ForeignKey("self")
    is_edited = Boolean()
    is_deleted = Boolean()
    created_at = Timestamptz()
    created_by = Text(required=True)

    @classmethod
    def objects(cls, *prefetch: ForeignKey | list[ForeignKey]) -> Objects:
        return (
            super().objects(*prefetch).where().order_by(cls.created_at, ascending=False)
        )

    @classmethod
    def all_objects(cls, *prefetch: ForeignKey | list[ForeignKey]) -> Objects:
        """
        Passes through to super().objects() without filtering deleted items.
        """
        return super().objects(*prefetch)

    @classmethod
    def select(
        cls, *columns: Selectable | str, exclude_secrets: bool = False
    ) -> Select:
        return (
            super()
            .select(*columns, exclude_secrets=exclude_secrets)
            .where()
            .order_by(cls.created_at, ascending=False)
        )

    @classmethod
    def all_select(
        cls, *columns: Selectable | str, exclude_secrets: bool = False
    ) -> Select:
        """
        Passes through to super().select() without filtering deleted items.
        """
        return super().select(*columns, exclude_secrets=exclude_secrets)
