import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture


def test_liveness_probe(test_client: TestClient) -> None:
    """Test successful liveness probe."""
    resp = test_client.get("/livez")
    assert resp.status_code == status.HTTP_204_NO_CONTENT


def test_readiness_probe(test_client: TestClient) -> None:
    """Test successful readiness probe."""
    resp = test_client.get("/readyz")
    assert resp.status_code == status.HTTP_200_OK


def test_readiness_probe_with_missing_engine(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    """Test readiness probe with no result from engine_finder()."""
    engine_finder = mocker.patch("bullsquid.status.views.engine_finder")
    engine_finder.return_value = None

    with pytest.raises(RuntimeError):
        test_client.get("/readyz")
