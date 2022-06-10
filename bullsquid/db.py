"""Database access layer."""
from typing import Any, Type
from uuid import UUID

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
