"""Defines the router for endpoints in the customer wallet system."""
from fastapi import APIRouter

from .stuff_lookups.views import router as stuff_lookups_router

router = APIRouter(prefix="/hackathon", tags=["Stuff Lookups"])
router.include_router(stuff_lookups_router)
