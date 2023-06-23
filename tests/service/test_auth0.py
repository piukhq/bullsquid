"""Tests for the transaction matching service interface."""

from aiohttp import ClientResponseError
from aioresponses import aioresponses
from fastapi import status
import pytest

from bullsquid.service.auth0 import Auth0ServiceInterface


async def test_get_user_profile(mock_responses: aioresponses) -> None:
    mock_responses.post(
        "https://testbink.com/oauth/token",
        status=status.HTTP_200_OK,
        payload={
            "token_type": "Bearer",
            "access_token": "test_token",
        },
    )
    mock_responses.get(
        "https://testbink.com/api/v2/users/test_user_id",
        status=status.HTTP_200_OK,
        payload={"test": "success"},
    )
    auth0 = Auth0ServiceInterface("https://testbink.com")
    resp = await auth0.get_user_profile("test_user_id")
    assert resp == {"test": "success"}


async def test_get_user_profile_expired_token(mock_responses: aioresponses) -> None:
    mock_responses.post(
        "https://testbink.com/oauth/token",
        repeat=True,
        status=status.HTTP_200_OK,
        payload={
            "token_type": "Bearer",
            "access_token": "test_token",
        },
    )
    mock_responses.get(
        "https://testbink.com/api/v2/users/test_user_id",
        repeat=True,
        status=status.HTTP_401_UNAUTHORIZED,
        payload={"message": "Expired token in request"},
    )
    auth0 = Auth0ServiceInterface("https://testbink.com")

    with pytest.raises(ClientResponseError) as e:
        await auth0.get_user_profile("test_user_id")

    assert e.value.status == status.HTTP_401_UNAUTHORIZED


async def test_get_user_profile_other_failure(mock_responses: aioresponses) -> None:
    mock_responses.post(
        "https://testbink.com/oauth/token",
        status=status.HTTP_200_OK,
        payload={
            "token_type": "Bearer",
            "access_token": "test_token",
        },
    )
    mock_responses.get(
        "https://testbink.com/api/v2/users/test_user_id",
        status=status.HTTP_403_FORBIDDEN,
        payload={"message": "Invalid scopes"},
    )
    auth0 = Auth0ServiceInterface("https://testbink.com")

    with pytest.raises(ClientResponseError) as e:
        await auth0.get_user_profile("test_user_id")

    assert e.value.status == status.HTTP_403_FORBIDDEN
