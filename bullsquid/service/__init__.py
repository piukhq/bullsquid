"""Service interface classes for any external API dependencies."""


from typing import Any, Mapping

import aiohttp


class ServiceInterface:
    """Base class for all service interfaces."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.headers: dict[str, str] = {}

    @staticmethod
    def _urljoin(*args: str) -> str:
        # a version of stdlib urljoin with less surprising behaviour.
        # https://stackoverflow.com/questions/1793261/how-to-join-components-of-a-path-when-you-are-constructing-a-url-in-python
        return "/".join(arg.strip("/") for arg in args)

    def _build_url(self, path: str) -> str:
        return self._urljoin(self.base_url, path)

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
