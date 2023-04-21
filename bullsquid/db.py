"""Database access layer."""
from typing import Any, Type, TypeVar
from uuid import UUID

from piccolo.columns import Column
from piccolo.query import Objects, Select
from piccolo.table import Table

from bullsquid.merchant_data.tables import BaseTable


class NoSuchRecord(Exception):
    """Raised when the requested record could not be found."""

    def __init__(self, table: Type[Table], *args: Any):
        super().__init__(*args)
        self.table = table


class InvalidData(Exception):
    """Raised when the data given for an operation cannot be used."""

    def __init__(self, table: Type[Table], *args: Any):
        super().__init__(*args)
        self.table = table


async def fields_are_unique(
    model: Type[BaseTable],
    fields: dict[Column, Any],
    *,
    exclude_pk: UUID | None = None,
) -> bool:
    """Returns true if the given field on the given table is unique, false otherwise."""
    if any(v is None for v in fields.values()):
        # null values are always unique
        return True

    duplicates_exist = model.all_exists()

    for column, value in fields.items():
        duplicates_exist = duplicates_exist.where(column == value)

    if exclude_pk:
        duplicates_exist = duplicates_exist.where(getattr(model, "pk") != exclude_pk)

    return not await duplicates_exist


Paginatable = TypeVar("Paginatable", Select, Objects)


def paginate(query: Paginatable, *, n: int, p: int) -> Paginatable:
    """
    Applies pagination to the given select query.
    `n` controls how many results are in the page.
    `p` controls which page of results is returned, starting with page #1.
    """
    if n < 1:
        raise ValueError("n must be >= 1")

    if p < 1:
        raise ValueError("p must be >= 1")

    return query.limit(n).offset(n * (p - 1))
