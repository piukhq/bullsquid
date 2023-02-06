"""
Database functions shared between locations and sub-locations.
"""
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.locations_common.models import (
    LocationOverviewMetadataBase,
    LocationPaymentSchemeCountResponse,
    SubLocationOverviewResponse,
)
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme


def create_location_overview_metadata_base(
    location: Location,
) -> LocationOverviewMetadataBase:
    """Creates a LocationMetadataResponse instance from the given location object."""
    return LocationOverviewMetadataBase(
        name=location.name,
        merchant_internal_id=location.merchant_internal_id,
        is_physical_location=location.is_physical_location,
        address_line_1=location.address_line_1,
        town_city=location.town_city,
        postcode=location.postcode,
    )


async def create_sub_location_overview_response(
    location: Location,
    *,
    payment_schemes: list[PaymentScheme],
) -> SubLocationOverviewResponse:
    """Creates a LocationOverviewResponse instance from the given merchant object."""
    return SubLocationOverviewResponse(
        date_added=location.date_added,
        location_ref=location.pk,
        location_status=location.status,
        location_metadata=create_location_overview_metadata_base(location),
        payment_schemes=[
            LocationPaymentSchemeCountResponse(
                scheme_slug=payment_scheme.slug,
                count=0,
            )
            for payment_scheme in payment_schemes
        ],
    )
