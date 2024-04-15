"""Tests the liveness and readiness endpoints in the status API."""

from asyncio import Future
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from piccolo.apps.migrations.commands.check import MigrationStatus


@pytest.fixture
def latest_migrations() -> Generator[None, None, None]:
    """Mocks the Piccolo migrations check manager to pretend all migrations have run."""
    result: Future[list[MigrationStatus]] = Future()
    result.set_result([])

    with patch("bullsquid.status.views.CheckMigrationManager") as manager:
        manager.return_value.get_migration_statuses.return_value = result
        yield


@pytest.fixture
def unused_migrations() -> Generator[None, None, None]:
    """
    Mocks the Piccolo migrations check manager to pretend one migration hasn't run yet.
    """
    result: Future[list[MigrationStatus]] = Future()
    status = MigrationStatus(
        app_name="merchant_data",
        migration_id="test-migration-1",
        description="a test migration",
        has_ran=False,
    )
    result.set_result([status])

    with patch("bullsquid.status.views.CheckMigrationManager") as manager:
        manager.return_value.get_migration_statuses.return_value = result
        yield


def test_liveness_probe(test_client: TestClient) -> None:
    """Test successful liveness probe."""
    resp = test_client.get("/livez")
    assert resp.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.usefixtures("latest_migrations")
def test_readiness_probe_complete_migrations(test_client: TestClient) -> None:
    """Test successful readiness probe."""
    resp = test_client.get("/readyz")
    assert resp.status_code == status.HTTP_200_OK


@pytest.mark.usefixtures("unused_migrations")
def test_readiness_probe_incomplete_migrations(test_client: TestClient) -> None:
    """Test readiness probe with a migration that hasn't run yet."""
    resp = test_client.get("/readyz")
    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


def test_readiness_probe_no_engine(test_client: TestClient) -> None:
    """Test readiness probe with no result from engine_finder()."""
    with patch("bullsquid.status.views.engine_finder") as engine_finder:
        engine_finder.return_value = None
        resp = test_client.get("/readyz")
        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
