"""Defines the router for endpoints in the merchant data management system."""
from fastapi import APIRouter

from .identifiers.views import router as identifiers_router
from .merchants.views import router as merchants_router
from .plans.views import router as plans_router
from .primary_mids.views import router as primary_mids_router

router = APIRouter(tags=["Merchant Data Management"])
router.include_router(plans_router)
router.include_router(merchants_router)
router.include_router(primary_mids_router)
router.include_router(identifiers_router)
