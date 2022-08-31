from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from ward import test

from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.tables import LocationSecondaryMIDLink
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
    location_secondary_mid_link_factory,
    merchant_factory,
    plan_factory,
    primary_mid_factory,
    secondary_mid_factory,
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


@test("location with only a name has the correct title")
def _() -> None:
    location = Location(name="test location")
    assert location.title == "test location"


@test("location with mixed fields has the correct title")
def _() -> None:
    location = Location(name="test location", town_city="test town")
    assert location.title == "test location, test town"


@test("location with all fields has the correct title")
def _() -> None:
    location = Location(
        name="test location",
        address_line_1="1 test street",
        town_city="test town",
        postcode="T35T L0C",
    )
    assert location.title == "test location, 1 test street, test town, T35T L0C"


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


@test("can list locations excluding a secondary mid")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    payment_schemes = await default_payment_schemes()
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    locations = [
        await location_factory(merchant=merchant),
        await location_factory(merchant=merchant),
        await location_factory(merchant=merchant),
        await location_factory(merchant=merchant),
        await location_factory(merchant=merchant),
    ]

    # associate the first three locations with the secondary mid
    for location in locations[:3]:
        await location_secondary_mid_link_factory(
            location=location, secondary_mid=secondary_mid
        )

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        params={"exclude_secondary_mid": secondary_mid.pk},
    )

    assert resp.status_code == 200

    expected = await Location.objects().where(
        Location.pk.is_in([location.pk for location in locations[-2:]])
    )
    assert resp.json() == [
        await location_to_json(location, payment_schemes) for location in expected
    ]


@test("can't exclude a secondary mid that doesn't exist")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        params={"exclude_secondary_mid": str(uuid4())},
    )

    assert_is_not_found_error(resp, loc=["query", "exclude_secondary_mid"])


@test("can't exclude a secondary mid from a different merchant")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory()

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        params={"exclude_secondary_mid": secondary_mid.pk},
    )

    assert_is_not_found_error(resp, loc=["query", "exclude_secondary_mid"])


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


@test("can delete locations")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    locations = [
        await location_factory(merchant=merchant),
        await location_factory(merchant=merchant),
        await location_factory(merchant=merchant),
    ]

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/deletion",
        json={"location_refs": [str(location.pk) for location in locations]},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    assert resp.json() == [
        {"location_ref": str(location.pk), "location_status": "deleted"}
        for location in locations
    ]


@test("deleting locations with an empty list does nothing")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/deletion",
        json={"location_refs": []},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    assert resp.json() == []


@test("deleting a location with a linked primary MID clears the link")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory(merchant=merchant, location=location)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/deletion",
        json={"location_refs": [str(location.pk)]},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED

    primary_mid = await PrimaryMID.objects().get(PrimaryMID.pk == primary_mid.pk)
    assert primary_mid.location is None


@test("deleting a location with a linked secondary MID deletes the link")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    await location_secondary_mid_link_factory(location=location)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/deletion",
        json={"location_refs": [str(location.pk)]},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED

    assert not await LocationSecondaryMIDLink.exists().where(
        LocationSecondaryMIDLink.location == location
    )


@test("can't delete locations on a non-existent plan")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    locations = [
        await location_factory(merchant=merchant),
        await location_factory(merchant=merchant),
        await location_factory(merchant=merchant),
    ]

    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations/deletion",
        json={"location_refs": [str(location.pk) for location in locations]},
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can't delete locations on a non-existent merchant")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    locations = [
        await location_factory(merchant=merchant),
        await location_factory(merchant=merchant),
        await location_factory(merchant=merchant),
    ]

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/locations/deletion",
        json={"location_refs": [str(location.pk) for location in locations]},
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't delete non-existent locations")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/deletion",
        json={"location_refs": [str(uuid4()) for _ in range(3)]},
    )

    assert_is_not_found_error(resp, loc=["body", "location_refs"])


@test("can associate a primary mid with a location")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/locations/{location.pk}/mids",
        json={"mid_refs": [str(primary_mid.pk)]},
    )

    assert resp.status_code == status.HTTP_200_OK

    assert resp.json() == [
        {
            "mid_ref": str(primary_mid.pk),
            "payment_scheme_slug": primary_mid.payment_scheme.slug,
            "mid_value": primary_mid.mid,
        }
    ]


@test("can't associate a primary mid with a location on a different merchant")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory()

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/locations/{location.pk}/mids",
        json={"mid_refs": [str(primary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["body", "mid_ref"])


@test("can't associate a primary mid with a location that doesn't exist")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()
    primary_mid = await primary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/locations/{uuid4()}/mids",
        json={"mid_refs": [str(primary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


@test("can't associate a primary mid with a location on a non-existent merchant")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{uuid4()}/locations/{location.pk}/mids",
        json={"mid_refs": [str(primary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't associate a primary mid with a location on a non-existent plan")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations/{location.pk}/mids",
        json={"mid_refs": [str(primary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can associate a secondary mid with a location")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/locations/{location.pk}/secondary_mid_location_links",
        json={"secondary_mid_refs": [str(secondary_mid.pk)]},
    )

    assert resp.status_code == status.HTTP_201_CREATED

    link = (
        await LocationSecondaryMIDLink.select(LocationSecondaryMIDLink.pk)
        .where(
            LocationSecondaryMIDLink.location == location,
            LocationSecondaryMIDLink.secondary_mid == secondary_mid,
        )
        .first()
    )
    assert resp.json() == [
        {
            "link_ref": str(link["pk"]),
            "secondary_mid_ref": str(secondary_mid.pk),
            "payment_scheme_slug": secondary_mid.payment_scheme.slug,
            "secondary_mid_value": secondary_mid.secondary_mid,
        }
    ]


@test("can't associate a secondary mid with a location on a different merchant")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory()

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/locations/{location.pk}/secondary_mid_location_links",
        json={"secondary_mid_refs": [str(secondary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["body", "secondary_mid_ref"])


@test("can't associate a secondary mid with a location that doesn't exist")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/locations/{uuid4()}/secondary_mid_location_links",
        json={"secondary_mid_refs": [str(secondary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


@test("can't associate a secondary mid with a location on a non-existent merchant")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{uuid4()}/locations/{location.pk}/secondary_mid_location_links",
        json={"secondary_mid_refs": [str(secondary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't associate a secondary mid with a location on a non-existent plan")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations/{location.pk}/secondary_mid_location_links",
        json={"secondary_mid_refs": [str(secondary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test(
    "creating the same secondary mid association twice only creates a single database record"
)
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    """
    We don't actually need to check the database in this test - the unique
    constraint will prevent the insertion of a second association.
    """
    merchant = await merchant_factory()
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    location = await location_factory(merchant=merchant)

    url = f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/locations/{location.pk}/secondary_mid_location_links"
    json = {"secondary_mid_refs": [str(secondary_mid.pk)]}

    resp1 = test_client.post(url, json=json)
    assert resp1.status_code == status.HTTP_201_CREATED

    resp2 = test_client.post(url, json=json)
    assert resp2.status_code == status.HTTP_200_OK

    assert resp1.json()[0]["link_ref"] == resp2.json()[0]["link_ref"]
