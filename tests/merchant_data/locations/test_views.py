from uuid import uuid4

from fastapi.testclient import TestClient
from ward import test

from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from tests.fixtures import database, test_client
from tests.helpers import assert_is_not_found_error
from tests.merchant_data.factories import (
    default_payment_schemes,
    location_factory,
    merchant_factory,
    plan_factory,
)


async def location_to_json(
    location: Location, payment_schemes: list[PaymentScheme]
) -> dict:
    """Converts a location to its expected JSON representation."""
    return {
        "location_ref": str(location.pk),
        "location_metadata": {
            "name": location.name,
            "location_id": location.location_id,
            "merchant_internal_id": location.merchant_internal_id,
            "is_physical_location": location.is_physical_location,
            "address_line_1": location.address_line_1,
            "town_city": location.town_city,
            "postcode": location.postcode,
        },
        "location_status": location.status,
        "date_added": location.date_added.isoformat(),
        "payment_schemes": [
            {
                "label": payment_scheme.label,
                "scheme_code": payment_scheme.code,
                "count": 0,
            }
            for payment_scheme in payment_schemes
        ],
    }


@test("can list locations")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    payment_schemes = await default_payment_schemes()

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations")

    assert resp.status_code == 200
    location = await Location.objects().get(Location.pk == location.pk)
    assert resp.json() == [await location_to_json(location, payment_schemes)]


@test("can't list location with invalid plan")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()

    resp = test_client.get(f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations")

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can't list location with invalid merchant ref")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/locations")

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])
