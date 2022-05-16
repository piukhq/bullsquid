"""Test API error handling methods."""
import json
from unittest.mock import patch

from fastapi import status
from ward import test

from bullsquid.api.errors import (
    APIMultiError,
    ResourceNotFoundError,
    UniqueError,
    error_response,
)


@test("error response with default args is formatted correctly")
def _() -> None:
    with patch("bullsquid.api.errors.logger"):  # suppress logger output
        resp = error_response(Exception("Test exception"))

    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(resp.body) == {
        "detail": {
            "msg": "Unable to process request due to an internal error.",
            "event_id": None,
        }
    }


@test("error response with custom args is formatted correctly")
def _() -> None:
    with patch("bullsquid.api.errors.logger"):  # suppress logger output
        resp = error_response(
            Exception("Test exception"),
            status_code=status.HTTP_418_IM_A_TEAPOT,
            message="I'm a teapot",
        )

    assert resp.status_code == status.HTTP_418_IM_A_TEAPOT
    assert json.loads(resp.body) == {
        "detail": {
            "msg": "I'm a teapot",
            "event_id": None,
        }
    }


@test("ResourceNotFoundError is formatted correctly")
def _() -> None:
    ex = ResourceNotFoundError(loc=("test", "loc"), resource_name="TestResource")
    expected = [
        {
            "loc": ("test", "loc"),
            "msg": "TestResource not found.",
            "type": "ref_error",
        }
    ]
    assert ex.detail == expected


@test("UniqueError is formatted correctly")
def _() -> None:
    ex = UniqueError(loc=("test", "loc"))
    expected = [
        {
            "loc": ("test", "loc"),
            "msg": "Field must be unique: test.loc.",
            "type": "unique_error",
        }
    ]
    assert ex.detail == expected


@test("APIMultiError is formatted correctly")
def _() -> None:
    ex = APIMultiError(
        [
            ResourceNotFoundError(loc=("test", "loc"), resource_name="TestResource"),
            UniqueError(loc=("test", "loc")),
        ]
    )
    expected = [
        {
            "loc": ("test", "loc"),
            "msg": "TestResource not found.",
            "type": "ref_error",
        },
        {
            "loc": ("test", "loc"),
            "msg": "Field must be unique: test.loc.",
            "type": "unique_error",
        },
    ]
    assert ex.detail == expected
