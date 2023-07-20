from typing import Any

from aiohttp import ClientResponseError
from bullsquid.service import ServiceInterface
from bullsquid.settings import settings


class Auth0ServiceInterface(ServiceInterface):
    async def update_token(self) -> None:
        """Fetches an up to date token for auth0"""
        audience = f"{self.base_url}/api/v2/"
        token = await self.post(
            "/oauth/token",
            json={
                "client_id": settings.oauth.mgmt_client_id,
                "client_secret": settings.oauth.mgmt_client_secret,
                "audience": audience,
                "grant_type": "client_credentials",
            },
        )
        self.headers = {
            "Authorization": f"{token['token_type']} {token['access_token']}"
        }

    async def get(self, path: str, **kwargs: Any) -> dict:
        if "Authorization" not in self.headers:
            await self.update_token()

        try:
            return await super().get(path, **kwargs)
        except ClientResponseError as e:
            if e.status == 401:
                await self.update_token()
                return await super().get(path, **kwargs)
            else:
                raise

    async def get_user_profile(self, user_id: str) -> dict:
        return await self.get(f"/api/v2/users/{user_id}")
