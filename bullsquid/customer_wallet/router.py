"""Defines the router for endpoints in the customer wallet system."""

from fastapi import APIRouter

from .user_lookups.views import router as user_lookups_router

router = APIRouter(prefix="/customer_wallet", tags=["Customer Wallet"])
router.include_router(user_lookups_router)
