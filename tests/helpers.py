"""Helper functions for use in tests."""
from fastapi import status
from requests import Response
from ward import expect


def assert_is_uniqueness_error(resp: Response, *, loc: list[str]) -> None:
    """Asserts that the response is a uniqueness error."""
    expect.assert_is_not(resp.ok, True, "Expected an error status code")
    expect.assert_equal(
        resp.status_code, status.HTTP_409_CONFLICT, "Expected status code to be 409"
    )

    detail = resp.json()["detail"]
    expect.assert_equal(len(detail), 1, "Expected a single error")
    expect.assert_equal(detail[0]["loc"], loc, "Expected the error location to match")
    expect.assert_equal(
        detail[0]["type"], "unique_error", "Expected the error type to match"
    )


def assert_is_missing_field_error(resp: Response, *, loc: list[str]) -> None:
    """Asserts that the response is a uniqueness error."""
    expect.assert_is_not(resp.ok, True, "Expected an error status code")
    expect.assert_equal(
        resp.status_code,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Expected status code to be 422",
    )

    detail = resp.json()["detail"]
    expect.assert_equal(len(detail), 1, "Expected a single error")
    expect.assert_equal(detail[0]["loc"], loc, "Expected the error location to match")
    expect.assert_equal(
        detail[0]["type"], "value_error", "Expected the error type to match"
    )


def assert_is_not_found_error(resp: Response, *, loc: list[str]) -> None:
    """Asserts that the response is a not found error."""
    expect.assert_is_not(resp.ok, True, "Expected an error status code")
    expect.assert_equal(
        resp.status_code,
        status.HTTP_404_NOT_FOUND,
        "Expected status code to be 404",
    )

    detail = resp.json()["detail"]
    expect.assert_equal(len(detail), 1, "Expected a single error")
    expect.assert_equal(detail[0]["loc"], loc, "Expected the error location to match")
    expect.assert_equal(
        detail[0]["type"], "ref_error", "Expected the error type to match"
    )


def assert_is_value_error(resp: Response, *, loc: list[str]) -> None:
    """Asserts that the response is a value error."""
    expect.assert_is_not(resp.ok, True, "Expected an error status code")
    expect.assert_equal(
        resp.status_code,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Expected status code to be 404",
    )

    detail = resp.json()["detail"]
    expect.assert_equal(len(detail), 1, "Expected a single error")
    expect.assert_equal(detail[0]["loc"], loc, "Expected the error location to match")
    expect.assert_equal(
        detail[0]["type"], "value_error", "Expected the error type to match"
    )
