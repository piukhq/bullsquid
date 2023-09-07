"""
Base merchant data tables.
"""

from typing import Sequence
from piccolo.columns import UUID, ForeignKey, Selectable, Text, Timestamptz, Column
from piccolo.query import Count, Objects, Select
from piccolo.query.methods.select import Count as SelectCount
from piccolo.query.methods.exists import Exists
from piccolo.table import Table

from bullsquid.merchant_data.enums import ResourceStatus


class BaseTable(Table):
    """
    Base table with a UUID primary key, status, and objects/select overrides
    for soft deletion.
    """

    pk = UUID(primary_key=True)
    status = Text(choices=ResourceStatus, default=ResourceStatus.ACTIVE)
    created = Timestamptz()

    @property
    def display_text(self) -> str:
        """
        The pretty printable text for this table.
        """
        raise NotImplementedError

    @classmethod
    def objects(cls, *prefetch: ForeignKey | list[ForeignKey]) -> Objects:
        return (
            super()
            .objects(*prefetch)
            .where(cls.status != ResourceStatus.DELETED)
            .order_by(cls.created, ascending=False)
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
        q = (
            super()
            .select(*columns, exclude_secrets=exclude_secrets)
            .where(cls.status != ResourceStatus.DELETED)
        )

        # if there's a count(*) involved, we don't want to order the results
        if not any(isinstance(c, SelectCount) for c in columns):
            q = q.order_by(cls.created, ascending=False)

        return q

    @classmethod
    def all_select(
        cls, *columns: Selectable | str, exclude_secrets: bool = False
    ) -> Select:
        """
        Passes through to super().select() without filtering deleted items.
        """
        return super().select(*columns, exclude_secrets=exclude_secrets)

    @classmethod
    def count(
        cls, column: Column | None = None, distinct: Sequence[Column] | None = None
    ) -> Count:
        return super().count().where(cls.status != ResourceStatus.DELETED)

    @classmethod
    def all_count(cls) -> Count:
        """
        Passes through to super().count() without filtering deleted items.
        """
        return super().count()

    @classmethod
    def exists(cls) -> Exists:
        return super().exists().where(cls.status != ResourceStatus.DELETED)

    @classmethod
    def all_exists(cls) -> Exists:
        """
        Passes through to super().exists() without filtering deleted items.
        """
        return super().exists()
