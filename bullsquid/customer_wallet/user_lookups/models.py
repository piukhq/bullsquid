"""Request & response Pydantic models for the user lookups API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class User(BaseModel):
    """User sub-model within a user lookup."""

    user_id: str
    channel: str
    display_text: str


class LookupRequest(BaseModel):
    """Lookup sub-model within a user lookup request."""

    type: str
    criteria: Any


class LookupResponse(LookupRequest):
    """Lookup sub-model within a user lookup response."""

    datetime: datetime


class UserLookupRequest(BaseModel):
    """Request model for the user lookup endpoints."""

    user: User
    lookup: LookupRequest


class UserLookupResponse(BaseModel):
    """Response model for the user lookup endpoints."""

    user: User
    lookup: LookupResponse
