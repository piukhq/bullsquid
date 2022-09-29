"""
Database table definitions for the comments module.
"""
from piccolo.columns import UUID, Array, Boolean, ForeignKey, Text, Timestamptz
from piccolo.table import Table

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
