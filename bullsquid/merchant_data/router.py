"""Defines the router for endpoints in the merchant data management system."""
from fastapi import APIRouter

from bullsquid.merchant_data.comments.views import router as comments_router
from bullsquid.merchant_data.csv_upload.views import router as csv_upload_router
from bullsquid.merchant_data.identifiers.views import router as identifiers_router
from bullsquid.merchant_data.locations.views import router as locations_router
from bullsquid.merchant_data.merchants.views import router as merchants_router
from bullsquid.merchant_data.plans.views import router as plans_router
from bullsquid.merchant_data.primary_mids.views import router as primary_mids_router
from bullsquid.merchant_data.secondary_mid_location_links.views import (
    router as secondary_mid_location_links_router,
)
from bullsquid.merchant_data.secondary_mids.views import router as secondary_mids_router

router = APIRouter(tags=["Merchant Data Management"])
router.include_router(comments_router)
router.include_router(plans_router)
router.include_router(merchants_router)
router.include_router(primary_mids_router)
router.include_router(secondary_mids_router)
router.include_router(identifiers_router)
router.include_router(locations_router)
router.include_router(secondary_mid_location_links_router)
router.include_router(csv_upload_router)
