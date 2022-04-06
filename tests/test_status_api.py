"""Tests the liveness and readiness endpoints in the status API."""
from asyncio import Future

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from piccolo.apps.migrations.commands.check import MigrationStatus
from pytest_mock import MockerFixture


@pytest.fixture
def latest_migrations(mocker: MockerFixture) -> None:
    """Mocks the Piccolo migrations check manager to pretend all migrations have run."""
    manager = mocker.patch("bullsquid.status.views.CheckMigrationManager")
    result: Future[list[MigrationStatus]] = Future()
    result.set_result([])
    manager.return_value.get_migration_statuses.return_value = result


@pytest.fixture
def unused_migrations(mocker: MockerFixture) -> None:
    """Mocks the Piccolo migrations check manager to pretend one migration hasn't run yet."""
    manager = mocker.patch("bullsquid.status.views.CheckMigrationManager")
    result: Future[list[MigrationStatus]] = Future()
    status = MigrationStatus(
        app_name="merchant_data",
        migration_id="test-migration-1",
        description="a test migration",
        has_ran=False,
    )
    result.set_result([status])
    manager.return_value.get_migration_statuses.return_value = result


def test_liveness_probe(test_client: TestClient) -> None:
    """Test successful liveness probe."""
    resp = test_client.get("/livez")
    assert resp.status_code == status.HTTP_204_NO_CONTENT, resp.text


@pytest.mark.usefixtures("latest_migrations")
def test_readiness_probe(test_client: TestClient) -> None:
    """Test successful readiness probe."""
    resp = test_client.get("/readyz")
    assert resp.status_code == status.HTTP_200_OK, resp.text


@pytest.mark.usefixtures("unused_migrations")
def test_readiness_probe_unused_migration(test_client: TestClient) -> None:
    """Test readiness probe with a migration that hasn't run yet."""
    resp = test_client.get("/readyz")
    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE, resp.text


def test_readiness_probe_with_missing_engine(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    """Test readiness probe with no result from engine_finder()."""
    engine_finder = mocker.patch("bullsquid.status.views.engine_finder")
    engine_finder.return_value = None

    with pytest.raises(RuntimeError):
        test_client.get("/readyz")
