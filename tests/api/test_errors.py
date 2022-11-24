"""Test API error handling methods."""
import json
from unittest.mock import patch

from fastapi import status

from bullsquid.api.errors import (
    APIMultiError,
    ResourceNotFoundError,
    UniqueError,
    error_response,
)


def test_error_response_default_args() -> None:
    resp = error_response(Exception("Test exception"))

    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(resp.body) == {
        "detail": [
            {
                "msg": "Unable to process request due to an internal error.",
                "event_id": None,
            }
        ]
    }


def test_error_response_custom_args() -> None:
    resp = error_response(
        Exception("Test exception"),
        status_code=status.HTTP_418_IM_A_TEAPOT,
        message="I'm a teapot",
    )

    assert resp.status_code == status.HTTP_418_IM_A_TEAPOT
    assert json.loads(resp.body) == {
        "detail": [
            {
                "msg": "I'm a teapot",
                "event_id": None,
            }
        ]
    }


def test_resource_not_found_error() -> None:
    ex = ResourceNotFoundError(loc=["test", "loc"], resource_name="Test resource")
    expected = [
        {
            "loc": ["test", "loc"],
            "msg": "Test resource not found.",
            "type": "ref_error",
        }
    ]
    assert ex.detail == expected


def test_unique_error() -> None:
    ex = UniqueError(loc=["test", "loc"])
    expected = [
        {
            "loc": ["test", "loc"],
            "msg": "Field must be unique: test.loc.",
            "type": "unique_error",
        }
    ]
    assert ex.detail == expected


def test_api_multi_error() -> None:
    ex = APIMultiError(
        [
            ResourceNotFoundError(loc=["test", "loc"], resource_name="Test resource"),
            UniqueError(loc=["test", "loc"]),
        ]
    )
    expected = [
        {
            "loc": ["test", "loc"],
            "msg": "Test resource not found.",
            "type": "ref_error",
        },
        {
            "loc": ["test", "loc"],
            "msg": "Field must be unique: test.loc.",
            "type": "unique_error",
        },
    ]
    assert ex.detail == expected
