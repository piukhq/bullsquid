"""Reusable Pydantic validators."""


def string_must_not_be_blank(value: str | None) -> str | None:
    """
    Validate that the provided string field is not blank.
    """
    if value is not None and not value.strip():
        raise ValueError("must not be blank if not null")

    return value
