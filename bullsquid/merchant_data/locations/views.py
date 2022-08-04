"""Endpoints that operate on locations"""
from uuid import UUID

from fastapi import APIRouter, Query

from bullsquid.api.errors import ResourceNotFoundError
from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.merchants.models import MerchantOverviewResponse
from bullsquid.merchant_data.payment_schemes.db import list_payment_schemes
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme

from . import db
from .models import (
    LocationMetadataResponse,
    LocationOverviewResponse,
    LocationPaymentSchemeCountResponse,
)

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/locations")


def create_location_metadata_response(
    location: db.LocationResult,
) -> LocationMetadataResponse:
    """Creates a LocationMetadataResponse instance from the given location object."""
    return LocationMetadataResponse(
        name=location["name"],
        location_id=location["location_id"],
        merchant_internal_id=location["merchant_internal_id"],
        is_physical_location=location["is_physical_location"],
        address_line_1=location["address_line_1"],
        town_city=location["town_city"],
        postcode=location["postcode"],
    )


async def create_location_overview_response(
    location: db.LocationResult, payment_schemes: list[PaymentScheme]
) -> LocationOverviewResponse:
    """Creates a MerchantOverviewResponse instance from the given merchant object."""
    return LocationOverviewResponse(
        date_added=location["date_added"],
        location_ref=location["pk"],
        location_status=location["status"],
        location_metadata=create_location_metadata_response(location),
        payment_schemes=[
            LocationPaymentSchemeCountResponse(
                label=payment_scheme.label,
                scheme_code=payment_scheme.code,
                count=0,
            )
            for payment_scheme in payment_schemes
        ],
    )


@router.get("", response_model=list[LocationOverviewResponse])
async def list_locations(
    plan_ref: UUID,
    merchant_ref: UUID,
    n: int = Query(default=10),
    p: int = Query(default=1),
) -> list[MerchantOverviewResponse]:
    """List locations on a merchant."""
    try:
        locations = await db.list_locations(
            plan_ref=plan_ref, merchant_ref=merchant_ref, n=n, p=p
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

    payment_schemes = await list_payment_schemes()
    return [
        await create_location_overview_response(location, payment_schemes)
        for location in locations
    ]
