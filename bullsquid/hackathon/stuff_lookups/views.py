"""Customer wallet API endpoints."""
from aiohttp import ClientSession
from fastapi import APIRouter, Response

from bullsquid.settings import settings

router = APIRouter(prefix="/stuff_lookups")


@router.get("/users")
async def list_membership_cards(u: str) -> str:
    """List user lookups for the given user header."""

    async with ClientSession() as session:
        async with session.get(
            f"{settings.hermes_url}/ubiquity/users/lookup?s={u}",
            headers={"Authorization": f"token {settings.service_api_key}"},
        ) as resp:
            return Response(content=(await resp.text()), media_type="application/json")
