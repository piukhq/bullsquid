"""Service interface classes for any external API dependencies."""


from typing import Any, Mapping
from urllib.parse import urljoin

import aiohttp


class ServiceInterface:
    """Base class for all service interfaces."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.headers: dict[str, str] = {}

    def _build_url(self, path: str) -> str:
        return urljoin(self.base_url, path)

    async def get(self, path: str, **kwargs: Any) -> dict:
        """
        Perform a GET request. Returns the JSON response.
        Keyword arguments are placed into the query string.
        """
        url = self._build_url(path)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, params=kwargs, headers=self.headers
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def post(self, path: str, json: Mapping) -> dict:
        """
        Perform a POST request. Returns the JSON response.
        """
        url = self._build_url(path)
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=json, headers=self.headers) as response:
                response.raise_for_status()
                return await response.json()
