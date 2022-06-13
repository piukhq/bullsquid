"""Database access layer."""
from typing import Any, Type
from uuid import UUID

from piccolo.query import Select
from piccolo.table import Table


class NoSuchRecord(Exception):
    """Raised when the requested record could not be found."""


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


def paginate(query: Select, *, n: int, p: int) -> Select:
    """
    Applies pagination to the given select query.
    `n` controls how many results are in the page.
    `p` controls which page of results is returned, starting with page #1.
    """
    if n < 0:
        raise ValueError("n must be >= 0")

    if p < 1:
        raise ValueError("p must be >= 1")

    return query.limit(n).offset(n * (p - 1))
