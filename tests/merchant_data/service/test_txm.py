"""Tests for the transaction matching service interface."""

from unittest.mock import MagicMock, patch

from aioresponses import aioresponses
from fastapi import status

from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.psimis.tables import PSIMI
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from bullsquid.merchant_data.service.txm import (
    TXMServiceInterface,
    create_txm_service_interface,
)
from tests.helpers import Factory


async def test_onboard_mids(
    primary_mid_factory: Factory[PrimaryMID],
    mock_responses: aioresponses,
) -> None:
    primary_mid = await primary_mid_factory()
    mock_responses.post(
        "https://testbink.com/txm/identifiers",
        status=status.HTTP_200_OK,
        payload={"test": "success"},
    )
    txm = TXMServiceInterface("https://testbink.com")
    resp = await txm.onboard_mids({primary_mid.pk})
    assert resp == {"test": "success"}


async def test_onboard_secondary_mids(
    secondary_mid_factory: Factory[SecondaryMID],
    mock_responses: aioresponses,
) -> None:
    secondary_mid = await secondary_mid_factory()
    mock_responses.post(
        "https://testbink.com/txm/identifiers",
        status=status.HTTP_200_OK,
        payload={"test": "success"},
    )
    txm = TXMServiceInterface("https://testbink.com")
    resp = await txm.onboard_secondary_mids({secondary_mid.pk})
    assert resp == {"test": "success"}


async def test_onboard_psimis(
    psimi_factory: Factory[PSIMI],
    mock_responses: aioresponses,
) -> None:
    psimi = await psimi_factory()
    mock_responses.post(
        "https://testbink.com/txm/identifiers",
        status=status.HTTP_200_OK,
        payload={"test": "success"},
    )
    txm = TXMServiceInterface("https://testbink.com")
    resp = await txm.onboard_psimis({psimi.pk})
    assert resp == {"test": "success"}


async def test_offboard_mids(
    primary_mid_factory: Factory[PrimaryMID],
    mock_responses: aioresponses,
) -> None:
    primary_mid = await primary_mid_factory()
    mock_responses.post(
        "https://testbink.com/txm/identifiers/deletion",
        status=status.HTTP_200_OK,
        payload={"test": "success"},
    )
    txm = TXMServiceInterface("https://testbink.com")
    resp = await txm.offboard_mids({primary_mid.pk})
    assert resp == {"test": "success"}


async def test_offboard_secondary_mids(
    secondary_mid_factory: Factory[SecondaryMID],
    mock_responses: aioresponses,
) -> None:
    secondary_mid = await secondary_mid_factory()
    mock_responses.post(
        "https://testbink.com/txm/identifiers/deletion",
        status=status.HTTP_200_OK,
        payload={"test": "success"},
    )
    txm = TXMServiceInterface("https://testbink.com")
    resp = await txm.offboard_secondary_mids({secondary_mid.pk})
    assert resp == {"test": "success"}


async def test_offboard_psimis(
    psimi_factory: Factory[PSIMI],
    mock_responses: aioresponses,
) -> None:
    psimi = await psimi_factory()
    mock_responses.post(
        "https://testbink.com/txm/identifiers/deletion",
        status=status.HTTP_200_OK,
        payload={"test": "success"},
    )
    txm = TXMServiceInterface("https://testbink.com")
    resp = await txm.offboard_psimis({psimi.pk})
    assert resp == {"test": "success"}


def test_real_interface() -> None:
    with patch(
        "bullsquid.merchant_data.service.txm.settings.txm.base_url",
        "https://testbink.com",
    ):
        txm = create_txm_service_interface()
        assert isinstance(txm, TXMServiceInterface)


def test_mock_interface() -> None:
    with patch("bullsquid.merchant_data.service.txm.settings.txm.base_url", None):
        txm = create_txm_service_interface()
        assert isinstance(txm, MagicMock)
