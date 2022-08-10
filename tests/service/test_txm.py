"""Tests for the transaction matching service interface."""
from importlib import reload
from unittest.mock import MagicMock, patch

from aioresponses import aioresponses
from fastapi import status
from ward import test

from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.service.txm import TXMServiceInterface, create_txm_service_interface
from tests.fixtures import mock_responses
from tests.merchant_data.factories import primary_mid


@test("the onboard_mids method sends a request to the correct url")
async def _(
    mock_responses: aioresponses = mock_responses,
    primary_mid: PrimaryMID = primary_mid,
) -> None:
    mock_responses.post(
        "https://testbink.com/txm/mids/",
        status=status.HTTP_200_OK,
        payload={"test": "success"},
    )
    txm = TXMServiceInterface("https://testbink.com")
    resp = await txm.onboard_mids([primary_mid.pk])
    assert resp == {"test": "success"}


@test("the offboard_mids method sends a request to the correct url")
async def _(
    mock_responses: aioresponses = mock_responses,
    primary_mid: PrimaryMID = primary_mid,
) -> None:
    mock_responses.post(
        "https://testbink.com/txm/mids/deletion",
        status=status.HTTP_200_OK,
        payload={"test": "success"},
    )
    txm = TXMServiceInterface("https://testbink.com")
    resp = await txm.offboard_mids([primary_mid.pk])
    assert resp == {"test": "success"}


@test("importing the txm service with a TXM base URL sets up a real interface")
def _() -> None:
    with patch("bullsquid.service.txm.settings.txm.base_url", "https://testbink.com"):
        txm = create_txm_service_interface()
        assert isinstance(txm, TXMServiceInterface)


@test("importing the txm service without a TXM base URL sets up a mock interface")
def _() -> None:
    with patch("bullsquid.service.txm.settings.txm.base_url", None):
        txm = create_txm_service_interface()
        assert isinstance(txm, MagicMock)
