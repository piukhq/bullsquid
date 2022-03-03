"""Defines endpoints under the /merchants prefix"""
from typing import Any, Mapping, TypeAlias

from fastapi import APIRouter, Response
from pydantic import BaseModel
from starlette.status import HTTP_204_NO_CONTENT

from bullsquid.mids.api.errors import MerchantNotFoundError
from bullsquid.mids.models import MerchantIn, MerchantOut
from bullsquid.mids.tables import Merchant, PaymentScheme

router = APIRouter(prefix="/merchants")

ViewResponse: TypeAlias = (
    Response | Mapping[str, Any] | list[Mapping[str, Any]] | BaseModel | list[BaseModel]
)


@router.get("/", response_model=list[MerchantOut])
async def merchants() -> ViewResponse:
    """List all Merchants.

    Returns:
        list[dict]: list of merchant details in MerchantOut format.
    """
    return await Merchant.select(
        Merchant.payment_schemes(PaymentScheme.slug, as_list=True),
        *Merchant.all_columns(),
    )


@router.post("/", response_model=MerchantOut)
async def create_merchant(merchant_model: MerchantIn) -> ViewResponse:
    """Create a new Merchant."""
    merchant_data = merchant_model.dict()
    payment_scheme_slugs = merchant_data.pop("payment_schemes")

    payment_schemes = await PaymentScheme.objects().where(
        PaymentScheme.slug.is_in(payment_scheme_slugs)
    )

    merchant = Merchant(**merchant_data)
    await merchant.save()
    await merchant.add_m2m(
        *payment_schemes,
        m2m=Merchant.payment_schemes,
    )

    merchant_data = merchant.to_dict()
    merchant_data["payment_schemes"] = [
        payment_scheme.slug for payment_scheme in payment_schemes
    ]
    return merchant_data


@router.put("/{merchant_ref}", response_model=MerchantOut)
async def update_merchant(
    merchant_ref: str, merchant_model: MerchantIn
) -> ViewResponse:
    """Update a merchant's details."""
    merchant = await Merchant.objects().get(Merchant.pk == merchant_ref)
    if not merchant:
        raise MerchantNotFoundError

    for key, value in merchant_model.dict().items():
        setattr(merchant, key, value)

    await merchant.save()

    return merchant.to_dict()


@router.delete("/{merchant_ref}")
async def delete_merchant(merchant_ref: str) -> ViewResponse:
    """Delete a merchant."""
    merchant = await Merchant.objects().get(Merchant.pk == merchant_ref)
    if not merchant:
        raise MerchantNotFoundError

    await merchant.remove()

    return Response(status_code=HTTP_204_NO_CONTENT)
