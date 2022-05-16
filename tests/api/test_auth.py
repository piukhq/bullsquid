"""Tests related to API authentication handling."""
from fastapi import status
from fastapi.testclient import TestClient
from ward import test

from settings import settings
from tests.fixtures import auth_header, database, test_client


@test("valid auth header returns a successful response")
def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    resp = test_client.get("/api/v1/plans", headers=auth_header)
    assert resp.ok


@test("invalid auth header format returns 401 unauthorized")
def _(_db: None = database, test_client: TestClient = test_client) -> None:
    resp = test_client.get("/api/v1/plans", headers={"Authorization": "nothing"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@test("invalid auth header prefix returns 401 unauthorized")
def _(_db: None = database, test_client: TestClient = test_client) -> None:
    resp = test_client.get(
        "/api/v1/plans",
        headers={"Authorization": "nothing abc123"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@test("invalid API key returns 401 unauthorized")
def _(_db: None = database, test_client: TestClient = test_client) -> None:
    resp = test_client.get(
        "/api/v1/plans",
        headers={"Authorization": f"token {settings.api_key + 'BADBADBAD'}"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@test("no auth header returns 403 forbidden")
def _(_db: None = database, test_client: TestClient = test_client) -> None:
    resp = test_client.get("/api/v1/plans")

    # NOTE: This should be a 401, but FastAPI currently returns a 403
    # https://github.com/tiangolo/fastapi/issues/2026
    # https://github.com/tiangolo/fastapi/pull/2120
    assert resp.status_code == status.HTTP_403_FORBIDDEN
