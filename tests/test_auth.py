"""Tests related to API authentication handling."""
from fastapi import status
from fastapi.testclient import TestClient

from settings import settings


def test_valid_auth(test_client: TestClient) -> None:
    """Test making a request with a valid API key."""
    resp = test_client.get(
        "/merchant_data/v1/merchants", headers={"Authorization": settings.api_key}
    )
    assert resp.ok


def test_invalid_auth(test_client: TestClient) -> None:
    """Test making a request with an invalid API key."""
    resp = test_client.get(
        "/merchant_data/v1/merchants",
        headers={"Authorization": settings.api_key + "BADBADBAD"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_no_auth(test_client: TestClient) -> None:
    """Test making a request with no auth header."""
    resp = test_client.get("/merchant_data/v1/merchants")
    assert resp.status_code == status.HTTP_403_FORBIDDEN
