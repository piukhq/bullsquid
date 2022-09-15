"""Database access layer."""
from typing import Any, Type, TypeVar
from uuid import UUID

from piccolo.query import Objects, Select
from piccolo.table import Table


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


async def field_is_unique(
    model: Type[Table], field: str, value: Any, *, pk: UUID | None = None
) -> bool:
    """Returns true if the given field on the given table is unique, false otherwise."""
    if value is None:
        # null values are always unique
        return True

    field = getattr(model, field)
    if pk:
        pk_field = getattr(model, "pk")
        return not await model.exists().where(pk_field != pk, field == value)
    return not await model.exists().where(field == value)


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
