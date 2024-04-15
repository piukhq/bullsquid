"""Tests for the service interface base class."""

import pytest
from aiohttp import ClientResponseError
from aioresponses import aioresponses
from fastapi import status

from bullsquid.service import ServiceInterface


async def test_get_success(mock_responses: aioresponses) -> None:
    mock_responses.get(
        "https://binktest.com/api/v1/test",
        status=status.HTTP_200_OK,
        payload={"test": "success"},
    )
    service = ServiceInterface("https://binktest.com")
    resp = await service.get("/api/v1/test")
    assert resp == {"test": "success"}


async def test_get_error(mock_responses: aioresponses) -> None:
    mock_responses.get(
        "https://binktest.com/api/v1/test",
        status=status.HTTP_400_BAD_REQUEST,
        payload={"test": "failure"},
    )
    service = ServiceInterface("https://binktest.com")
    with pytest.raises(ClientResponseError) as ex:
        await service.get("/api/v1/test")
    assert ex.value.code == status.HTTP_400_BAD_REQUEST


async def test_post_success(mock_responses: aioresponses) -> None:
    mock_responses.post(
        "https://binktest.com/api/v1/test",
        status=status.HTTP_200_OK,
        payload={"test": "success"},
    )
    service = ServiceInterface("https://binktest.com")
    resp = await service.post("/api/v1/test", {"test": "test"})
    assert resp == {"test": "success"}


async def test_post_error(mock_responses: aioresponses) -> None:
    mock_responses.post(
        "https://binktest.com/api/v1/test",
        status=status.HTTP_400_BAD_REQUEST,
        payload={"test": "failure"},
    )
    service = ServiceInterface("https://binktest.com")
    with pytest.raises(ClientResponseError) as ex:
        await service.post("/api/v1/test", {"test": "test"})
    assert ex.value.status == status.HTTP_400_BAD_REQUEST


async def test_join() -> None:
    parts, expected = ("https://test.url", "a/b"), "https://test.url/a/b"
    assert ServiceInterface._urljoin(*parts) == expected


async def test_join_slashes() -> None:
    parts, expected = ("https://test.url/", "/a/b/"), "https://test.url/a/b"
    assert ServiceInterface._urljoin(*parts) == expected


async def test_join_path() -> None:
    parts, expected = ("https://test.url/a", "b/c"), "https://test.url/a/b/c"
    assert ServiceInterface._urljoin(*parts) == expected


async def test_join_path_slashes() -> None:
    parts, expected = ("https://test.url/a/", "/b/c/"), "https://test.url/a/b/c"
    assert ServiceInterface._urljoin(*parts) == expected
