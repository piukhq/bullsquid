"""Tests related to API authentication handling."""
from fastapi import status
from fastapi.testclient import TestClient

from settings import settings


def test_valid_auth(test_client: TestClient, auth_header: dict) -> None:
    """Test making a request with a valid API key."""
    resp = test_client.get("/api/v1/plans", headers=auth_header)
    assert resp.ok


def test_invalid_auth_header_format(test_client: TestClient) -> None:
    """Test making a request with the auth header in the wrong format."""
    resp = test_client.get("/api/v1/plans", headers={"Authorization": "nothing"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_invalid_auth_header_prefix(test_client: TestClient) -> None:
    """Test making a request with an invalid prefix on the auth header."""
    resp = test_client.get(
        "/api/v1/plans",
        headers={"Authorization": "nothing abc123"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_invalid_api_key(test_client: TestClient) -> None:
    """Test making a request with an invalid API key."""
    resp = test_client.get(
        "/api/v1/plans",
        headers={"Authorization": f"token {settings.api_key + 'BADBADBAD'}"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_no_auth(test_client: TestClient) -> None:
    """Test making a request with no auth header."""
    resp = test_client.get("/api/v1/plans")

    # NOTE: This should be a 401, but FastAPI currently returns a 403
    assert resp.status_code == status.HTTP_403_FORBIDDEN
