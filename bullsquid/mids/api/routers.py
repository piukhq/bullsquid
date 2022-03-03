"""FastAPI app for the MID managment API."""
from fastapi import APIRouter

from bullsquid.mids.api.v1.routers import merchants

v1 = APIRouter(prefix="/v1")
v1.include_router(merchants.router)
