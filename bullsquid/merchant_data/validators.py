"""Reusable Pydantic validators."""

from typing import Generator

from pydantic import HttpUrl
from pydantic.typing import AnyCallable
from url_normalize import url_normalize

CallableGenerator = Generator[AnyCallable, None, None]


def string_must_not_be_blank(value: str | None) -> str | None:
    """
    Validate that the provided string field is not blank.
    """
    if value is not None and not value.strip():
        raise ValueError("must not be blank")

    return value


def nullify_blank_strings(value: str | None) -> str | None:
    """
    Allow blank strings to be returned as Null in certain cases
    """
    if value is None:
        return value
    null_value: str | None = value.strip()
    if null_value == "":
        null_value = None
    return null_value


class FlexibleUrl(HttpUrl):
    """URL validator for formatting incoming URLs"""

    @classmethod
    def __get_validators__(cls) -> CallableGenerator:
        yield cls.normalize_url
        yield from super().__get_validators__()

    @classmethod
    def normalize_url(cls, v: str) -> str:
        """Normalizes the url"""
        return url_normalize(v)
