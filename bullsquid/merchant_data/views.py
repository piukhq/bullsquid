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
    Plan,
    PlanWithPK,
)

router = APIRouter(prefix="/v1", tags=["Merchant Data Management"])


async def field_is_unique(
    model: Type[Table], field: str, value: Any, *, pk: UUID | None = None
) -> bool:
    """Returns true if the given field on the given table is unique, false otherwise."""
    if value is None:
        # null values are always unique
        return True

    field = getattr(model, field)
    if pk:
        pk_field = getattr(model, "pk")
        return not await model.exists().where(pk_field != pk, field == value)
    return not await model.exists().where(field == value)


@router.get("/plans", response_model=list[PlanWithPK])
async def list_plans() -> list[dict]:
    """List all plans."""
    return [l.to_dict() for l in await db.list_plans()]


@router.post("/plans", response_model=PlanWithPK)
async def create_plan(plan_data: Plan) -> dict:
    """Create a new plan."""
    plan_data = plan_data.dict()
    if errors := [
        UniqueError(loc=("body", field))
        for field in ["name", "slug", "plan_id"]
        if not await field_is_unique(db.Plan, field, plan_data[field])
    ]:
        raise APIMultiError(errors)

    plan = await db.create_plan(plan_data)
    return plan.to_dict()


@router.put("/plans/{plan_ref}", response_model=PlanWithPK)
async def update_plan(plan_ref: UUID, plan_data: Plan) -> dict:
    """Update a plan's details."""
    plan_data = plan_data.dict()
    if errors := [
        UniqueError(loc=("body", field))
        for field in ["name", "slug", "plan_id"]
        if not await field_is_unique(db.Plan, field, plan_data[field], pk=plan_ref)
    ]:
        raise APIMultiError(errors)

    try:
        plan = await db.update_plan(plan_ref, plan_data)
    except db.NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=("path", "plan_ref"), resource_name="Plan"
        ) from ex

    return plan.to_dict()


@router.get("/merchants", response_model=list[MerchantWithPK])
async def list_merchants() -> list[dict]:
    """List all Merchants."""
    return [m.to_dict() for m in await db.list_merchants()]


@router.post("/merchants", response_model=MerchantWithPK)
async def create_merchant(merchant_data: Merchant) -> dict:
    """Create a new Merchant."""
    merchant_data = merchant_data.dict()
    if errors := [
        UniqueError(loc=("body", field))
        for field in ["name", "slug", "plan_id"]
        if not await field_is_unique(db.Merchant, field, merchant_data[field])
    ]:
        raise APIMultiError(errors)

    merchant = await db.create_merchant(merchant_data)
    return merchant.to_dict()


@router.put("/merchants/{merchant_ref}", response_model=MerchantWithPK)
async def update_merchant(merchant_ref: UUID, merchant_data: Merchant) -> dict:
    """Update a merchant's details."""
    merchant_data = merchant_data.dict()
    if errors := [
        UniqueError(loc=("body", field))
        for field in ["name", "slug", "plan_id"]
        if not await field_is_unique(
            db.Merchant, field, merchant_data[field], pk=merchant_ref
        )
    ]:
        raise APIMultiError(errors)

    try:
        merchant = await db.update_merchant(merchant_ref, merchant_data)
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
    try:
        merchant = await db.get_merchant(merchant_ref)
    except db.NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=("path", "merchant_ref"), resource_name="Merchant"
        ) from ex

    if await db.Location.exists().where(
        db.Location.merchant == merchant,
        db.Location.location_id == location_data.location_id,
    ):
        raise UniqueError(loc=("body", "location_id"))

    location = await db.create_location(location_data.dict(), merchant=merchant)
    return location.to_dict()


@router.put(
    "/merchants/{merchant_ref}/locations/{location_ref}",
    response_model=LocationWithPK,
)
async def update_location(
    merchant_ref: UUID, location_ref: UUID, location_data: Location
) -> dict:
    """Update a locations's details."""
    try:
        merchant = await db.get_merchant(merchant_ref)
    except db.NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=("path", "merchant_ref"), resource_name="Merchant"
        ) from ex

    try:
        location = await db.update_location(
            location_ref, location_data.dict(), merchant=merchant
        )
    except db.NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=("path", "location_ref"), resource_name="Location"
        ) from ex

    return location.to_dict()
