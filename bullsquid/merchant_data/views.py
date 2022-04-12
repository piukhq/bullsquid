"""Defines endpoints under the /merchants prefix"""
from typing import Any, Type
from uuid import UUID

from fastapi import APIRouter
from piccolo.table import Table
from starlette import status

from bullsquid.api.errors import APIMultiError, ResourceNotFoundError, UniqueError
from bullsquid.merchant_data import db
from bullsquid.merchant_data.models import (
    Location,
    LocationWithPK,
    Merchant,
    MerchantWithPK,
)

router = APIRouter(prefix="/v1")


async def field_is_unique(
    model: Type[Table], field: str, value: Any, *, pk: UUID | None = None
) -> bool:
    """Returns true if the given field on the given table is unique, false otherwise."""
    field = getattr(model, field)
    if pk:
        pk_field = getattr(model, "pk")
        return not await model.exists().where(pk_field != pk, field == value)
    return not await model.exists().where(field == value)


@router.get("/merchants", response_model=list[MerchantWithPK])
async def merchants() -> list[dict]:
    """List all Merchants."""
    return [m.to_dict() for m in await db.list_merchants()]


@router.post("/merchants", response_model=MerchantWithPK)
async def create_merchant(merchant_data: Merchant) -> dict:
    """Create a new Merchant."""
    if errors := [
        UniqueError(loc=("body", field))
        for field in ["name", "slug", "plan_id"]
        if not await field_is_unique(db.Merchant, field, merchant_data.dict()[field])
    ]:
        raise APIMultiError(errors)

    merchant = await db.create_merchant(merchant_data.dict())
    return merchant.to_dict()


@router.put("/merchants/{merchant_ref}", response_model=MerchantWithPK)
async def update_merchant(merchant_ref: UUID, merchant_data: Merchant) -> dict:
    """Update a merchant's details."""
    if errors := [
        UniqueError(loc=("body", field))
        for field in ["name", "slug", "plan_id"]
        if not await field_is_unique(
            db.Merchant, field, merchant_data.dict()[field], pk=merchant_ref
        )
    ]:
        raise APIMultiError(errors)

    try:
        merchant = await db.update_merchant(merchant_ref, merchant_data.dict())
    except db.NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=("path", "merchant_ref"), resource_name="Merchant"
        ) from ex

    return merchant.to_dict()


@router.delete(
    "/merchants/{merchant_ref}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {}},
)
async def delete_merchant(merchant_ref: UUID) -> None:
    """Delete a merchant."""
    try:
        await db.delete_merchant(merchant_ref)
    except db.NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=("path", "merchant_ref"), resource_name="Merchant"
        ) from ex


@router.post("/merchants/{merchant_ref}/locations", response_model=LocationWithPK)
async def create_location(merchant_ref: UUID, location_data: Location) -> dict:
    """Create a location for a merchant."""
    merchant = await db.get_merchant(merchant_ref)

    if await db.Location.exists().where(
        db.Location.merchant == merchant,
        db.Location.location_id == location_data.location_id,
    ):
        raise UniqueError(loc=("body", "location_id"))

    location = await db.create_location(location_data.dict(), merchant=merchant)
    return location.to_dict()