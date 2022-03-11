"""Test API error handling methods."""
import json

from bullsquid.api.app import error_response


def test_error_response_default_args() -> None:
    """Test handling an error with default message and status code."""
    resp = error_response(Exception("Test exception"))
    assert resp.status_code == 500
    assert json.loads(resp.body) == {
        "detail": {
            "msg": "Unable to process request due to an internal error.",
            "event_id": None,
        }
    }


def test_error_response_custom_args() -> None:
    """Test handling an error with custom message and status code."""
    resp = error_response(
        Exception("Test exception"),
        status_code=418,
        message="I'm a teapot",
    )
    assert resp.status_code == 418
    assert json.loads(resp.body) == {
        "detail": {
            "msg": "I'm a teapot",
            "event_id": None,
        }
    }
