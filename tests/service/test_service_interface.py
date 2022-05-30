"""Tests for the service interface base class."""
from aiohttp import ClientResponseError
from aioresponses import aioresponses
from fastapi import status
from ward import raises, test

from bullsquid.service import ServiceInterface
from tests.fixtures import mock_responses


@test("the get method sends a request to the correct url")
async def _(mock_responses: aioresponses = mock_responses) -> None:
    mock_responses.get(
        "https://binktest.com/api/v1/test", status=200, payload={"test": "success"}
    )
    service = ServiceInterface("https://binktest.com")
    resp = await service.get("/api/v1/test")
    assert resp == {"test": "success"}


@test("the get method raises an exception if the response is not 2xx")
async def _(mock_responses: aioresponses = mock_responses) -> None:
    mock_responses.get(
        "https://binktest.com/api/v1/test", status=400, payload={"test": "failure"}
    )
    service = ServiceInterface("https://binktest.com")
    with raises(ClientResponseError) as ex:
        await service.get("/api/v1/test")
    assert ex.raised.code == status.HTTP_400_BAD_REQUEST


@test("the post method sends a request to the correct url")
async def _(mock_responses: aioresponses = mock_responses) -> None:
    mock_responses.post(
        "https://binktest.com/api/v1/test", status=200, payload={"test": "success"}
    )
    service = ServiceInterface("https://binktest.com")
    resp = await service.post("/api/v1/test", {"test": "test"})
    assert resp == {"test": "success"}


@test("the post method raises an exception if the response is not 2xx")
async def _(mock_responses: aioresponses = mock_responses) -> None:
    mock_responses.post(
        "https://binktest.com/api/v1/test", status=400, payload={"test": "failure"}
    )
    service = ServiceInterface("https://binktest.com")
    with raises(ClientResponseError) as ex:
        await service.post("/api/v1/test", {"test": "test"})
    assert ex.raised.code == status.HTTP_400_BAD_REQUEST