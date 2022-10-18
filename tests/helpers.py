from typing import Any, Protocol, TypeVar

from fastapi import status
from piccolo.table import Table
from requests import Response

T = TypeVar("T", bound=Table, covariant=True)


class Factory(Protocol[T]):
    async def __call__(self, *, persist: bool = True, **defaults: Any) -> T:
        pass


def assert_is_uniqueness_error(resp: Response, *, loc: list[str]) -> None:
    """Asserts that the response is a uniqueness error."""
    assert (
        resp.status_code == status.HTTP_409_CONFLICT
    ), f"Expected status code to be 409: {resp}\n{resp.text}"

    detail = resp.json()["detail"]
    assert len(detail) == 1, "Expected a single error"
    assert detail[0]["loc"] == loc
    assert detail[0]["type"] == "unique_error"


def assert_is_missing_field_error(resp: Response, *, loc: list[str]) -> None:
    """Asserts that the response is a missing field error."""
    assert (
        resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    ), f"Expected status code to be 422: {resp}\n{resp.text}"

    detail = resp.json()["detail"]
    assert len(detail) == 1, "Expected a single error"
    assert detail[0]["loc"] == loc
    assert detail[0]["type"] == "value_error.missing"


def assert_is_data_error(resp: Response, *, loc: list[str]) -> None:
    """Asserts that the response is a data error."""
    assert (
        resp.status_code == status.HTTP_409_CONFLICT
    ), f"Expected status code to be 409: {resp}\n{resp.text}"

    detail = resp.json()["detail"]
    assert len(detail) == 1, "Expected a single error"
    assert detail[0]["loc"] == loc
    assert detail[0]["type"] == "data_error"


def assert_is_not_found_error(resp: Response, *, loc: list[str]) -> None:
    """Asserts that the response is a not found error."""
    assert (
        resp.status_code == status.HTTP_404_NOT_FOUND
    ), f"Expected status code to be 404: {resp}\n{resp.text}"

    detail = resp.json()["detail"]
    assert len(detail) == 1, "Expected a single error"
    assert detail[0]["loc"] == loc
    assert detail[0]["type"] == "ref_error"


def assert_is_value_error(resp: Response, *, loc: list[str]) -> None:
    """Asserts that the response is a value error."""
    assert (
        resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    ), f"Expected status code to be 422: {resp}\n{resp.text}"

    detail = resp.json()["detail"]
    assert len(detail) == 1, "Expected a single error"
    assert detail[0]["loc"] == loc
    assert detail[0]["type"] == "value_error"


def assert_is_null_error(resp: Response, *, loc: list[str]) -> None:
    """Asserts that the response is a "null not allowed" error."""
    assert (
        resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    ), f"Expected status code to be 422: {resp}\n{resp.text}"

    detail = resp.json()["detail"]
    assert len(detail) == 1, "Expected a single error"
    assert detail[0]["loc"] == loc
    assert detail[0]["type"] == "type_error.none.not_allowed"
