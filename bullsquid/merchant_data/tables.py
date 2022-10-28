"""
Base merchant data tables.
"""

from typing import TYPE_CHECKING

from piccolo.columns import UUID, ForeignKey, Selectable, Text
from piccolo.query import Count, Objects, Select
from piccolo.table import Table

from bullsquid.merchant_data.enums import ResourceStatus


class TableWithPK(Table):
    """
    Base table with a UUID primary key.
    """

    pk = UUID(primary_key=True)

    @property
    def display_text(self) -> str:
        """
        The pretty printable text for this table.
        """
        raise NotImplementedError


if TYPE_CHECKING:
    _Base = Table
else:
    _Base = object


class SoftDeletable(_Base):  # pylint: disable=all
    """
    Table mixin with a status column and objects/select overrides for soft deletion.
    """

    status = Text(choices=ResourceStatus, default=ResourceStatus.ACTIVE)

    @classmethod
    def objects(cls, *prefetch: ForeignKey | list[ForeignKey]) -> Objects:
        return super().objects(*prefetch).where(cls.status != ResourceStatus.DELETED)

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
            .where(cls.status != ResourceStatus.DELETED)
        )

    @classmethod
    def all_select(
        cls, *columns: Selectable | str, exclude_secrets: bool = False
    ) -> Select:
        """
        Passes through to super().select() without filtering deleted items.
        """
        return super().select(*columns, exclude_secrets=exclude_secrets)

    @classmethod
    def count(cls) -> Count:
        return super().count().where(cls.status != ResourceStatus.DELETED)

    @classmethod
    def all_count(cls) -> Count:
        """
        Passes through to super().count() without filtering deleted items.
        """
        return super().count()
