"""Defines endpoints under the /merchants prefix"""
from typing import Any, Mapping, Type, TypeAlias

from fastapi import APIRouter, Response
from piccolo.table import Table
from pydantic import BaseModel
from starlette.status import HTTP_204_NO_CONTENT

from bullsquid.api.errors import APIMultiError, ResourceNotFoundError, UniqueError
from bullsquid.merchant_data import db
from bullsquid.merchant_data.models import Merchant, MerchantWithPK

router = APIRouter(prefix="/merchants")

ViewResponse: TypeAlias = (
    Response | Mapping[str, Any] | list[Mapping[str, Any]] | BaseModel | list[BaseModel]
)


async def field_is_unique(model: Type[Table], field: str, value: Any) -> bool:
    """Returns true if the given field on the given table is unique, false otherwise."""
    return not await model.exists().where(getattr(model, field) == value)


@router.get("", response_model=list[MerchantWithPK])
async def merchants() -> ViewResponse:
    """List all Merchants."""
    return [m.to_dict() for m in await db.list_merchants()]


@router.post("", response_model=MerchantWithPK)
async def create_merchant(merchant_data: Merchant) -> ViewResponse:
    """Create a new Merchant."""
    if errors := [
        UniqueError(loc=("body", field))
        for field in ["name", "slug", "plan_id"]
        if not await field_is_unique(db.Merchant, field, merchant_data.dict()[field])
    ]:
        raise APIMultiError(errors)

    merchant = await db.create_merchant(merchant_data.dict())
    return merchant.to_dict()


@router.put("/{merchant_ref}", response_model=MerchantWithPK)
async def update_merchant(merchant_ref: str, merchant_data: Merchant) -> ViewResponse:
    """Update a merchant's details."""
    try:
        merchant = await db.update_merchant(merchant_ref, merchant_data.dict())
    except db.NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=("path", "merchant_ref"), resource_name="Merchant"
        ) from ex

    return merchant.to_dict()


@router.delete("/{merchant_ref}")
async def delete_merchant(merchant_ref: str) -> ViewResponse:
    """Delete a merchant."""
    try:
        await db.delete_merchant(merchant_ref)
    except db.NoSuchRecord as ex:
        raise ResourceNotFoundError(
            loc=("path", "merchant_ref"), resource_name="Merchant"
        ) from ex

    return Response(status_code=HTTP_204_NO_CONTENT)
