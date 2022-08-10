from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from ward import test

from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from tests.fixtures import database, test_client
from tests.helpers import (
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_uniqueness_error,
    assert_is_value_error,
)
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


async def location_to_json_detail(
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
            "address_line_2": location.address_line_2,
            "county": location.county,
            "country": location.country,
        },
        "location_status": location.status,
        "date_added": location.date_added.isoformat(),
        "linked_mids_count": 0,
        "linked_secondary_mids_count": 0,
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

    assert resp.status_code == status.HTTP_200_OK
    location = await Location.objects().get(Location.pk == location.pk)
    assert resp.json() == [await location_to_json(location, payment_schemes)]


@test("can't list a location with invalid plan")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()

    resp = test_client.get(f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations")

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can't list a location with invalid merchant ref")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/locations")

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can get location details")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    payment_schemes = await default_payment_schemes()

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}"
    )

    assert resp.status_code == status.HTTP_200_OK
    location = await Location.objects().get(Location.pk == location.pk)
    assert resp.json() == await location_to_json_detail(location, payment_schemes)


@test("can't get detailed location with invalid location ref")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{uuid4()}"
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


@test("can't get location details with an invalid merchant ref")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/locations/{location.pk}"
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't get location details with an invalid plan ref")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations/{location.pk}"
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can create a location")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(persist=False, merchant=merchant)
    payment_schemes = await default_payment_schemes()

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        json={
            field: getattr(location, field)
            for field in [
                "name",
                "location_id",
                "merchant_internal_id",
                "is_physical_location",
                "address_line_1",
                "address_line_2",
                "town_city",
                "county",
                "country",
                "postcode",
            ]
        },
    )

    assert resp.status_code == status.HTTP_201_CREATED, resp.text

    location = await Location.objects().get(Location.pk == resp.json()["location_ref"])
    assert resp.json() == await location_to_json(location, payment_schemes)


@test("can't create a location on a non-existent plan")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()
    location = await location_factory(persist=False, merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations",
        json={
            field: getattr(location, field)
            for field in [
                "name",
                "location_id",
                "merchant_internal_id",
                "is_physical_location",
                "address_line_1",
                "address_line_2",
                "town_city",
                "county",
                "country",
                "postcode",
            ]
        },
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can't create a location on a non-existent merchant")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(persist=False, merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/locations",
        json={
            field: getattr(location, field)
            for field in [
                "name",
                "location_id",
                "merchant_internal_id",
                "is_physical_location",
                "address_line_1",
                "address_line_2",
                "town_city",
                "county",
                "country",
                "postcode",
            ]
        },
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't create a location without a location ID")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(persist=False, merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        json={
            field: getattr(location, field)
            for field in [
                "name",
                "merchant_internal_id",
                "is_physical_location",
                "address_line_1",
                "address_line_2",
                "town_city",
                "county",
                "country",
                "postcode",
            ]
        },
    )

    assert_is_missing_field_error(resp, loc=["body", "location_id"])


@test("can't create a location without a name")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(persist=False, merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        json={
            field: getattr(location, field)
            for field in [
                "location_id",
                "merchant_internal_id",
                "is_physical_location",
                "address_line_1",
                "address_line_2",
                "town_city",
                "county",
                "country",
                "postcode",
            ]
        },
    )

    assert_is_missing_field_error(resp, loc=["body", "name"])


@test("can't create a location without is_physical_location")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(persist=False, merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        json={
            field: getattr(location, field)
            for field in [
                "name",
                "location_id",
                "merchant_internal_id",
                "address_line_1",
                "address_line_2",
                "town_city",
                "county",
                "country",
                "postcode",
            ]
        },
    )

    assert_is_missing_field_error(resp, loc=["body", "is_physical_location"])


@test("can't create a location with duplicate location_id")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    existing_location = await location_factory(merchant=merchant)
    location = await location_factory(
        persist=False, merchant=merchant, location_id=existing_location.location_id
    )

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        json={
            field: getattr(location, field)
            for field in [
                "name",
                "location_id",
                "merchant_internal_id",
                "is_physical_location",
                "address_line_1",
                "address_line_2",
                "town_city",
                "county",
                "country",
                "postcode",
            ]
        },
    )

    assert_is_uniqueness_error(resp, loc=["body", "location_id"])


@test("can't create a physical location without address line 1")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(
        persist=False, merchant=merchant, is_physical_location=True
    )

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        json={
            field: getattr(location, field)
            for field in [
                "name",
                "location_id",
                "merchant_internal_id",
                "is_physical_location",
                "address_line_2",
                "town_city",
                "county",
                "country",
                "postcode",
            ]
        },
    )

    assert_is_value_error(resp, loc=["body", "__root__"])


@test("can't create a physical location without postcode")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(
        persist=False, merchant=merchant, is_physical_location=True
    )

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        json={
            field: getattr(location, field)
            for field in [
                "name",
                "location_id",
                "merchant_internal_id",
                "is_physical_location",
                "address_line_1",
                "address_line_2",
                "town_city",
                "county",
                "country",
            ]
        },
    )

    assert_is_value_error(resp, loc=["body", "__root__"])
