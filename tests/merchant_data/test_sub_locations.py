from typing import Any
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from tests.helpers import (
    Factory,
    assert_is_not_found_error,
    assert_is_uniqueness_error,
    assert_is_value_error,
)


async def sub_location_to_json(
    location: Location,
    payment_schemes: list[PaymentScheme],
) -> dict:
    """Converts a sub-location to its expected JSON representation."""
    data: dict[str, Any] = {
        "location_ref": str(location.pk),
        "location_metadata": {
            "name": location.name,
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
                "slug": payment_scheme.slug,
                "count": 0,
            }
            for payment_scheme in payment_schemes
        ],
    }

    return data


async def sub_location_to_json_detail(
    location: Location,
    parent: Location,
    payment_schemes: list[PaymentScheme],
) -> dict:
    """Converts a location to its expected JSON representation."""
    if not location.parent:
        raise ValueError("location passed to sub-location json helper")

    return {
        "parent_location": {
            "location_ref": str(parent.pk),
            "location_title": parent.display_text,
        },
        "sub_location": {
            "location_ref": str(location.pk),
            "location_metadata": {
                "name": location.name,
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
                    "slug": payment_scheme.slug,
                    "count": 0,
                }
                for payment_scheme in payment_schemes
            ],
        },
    }


async def test_create_sub_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    sub_location = await location_factory(persist=False, merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/sub_locations",
        json={
            field: getattr(sub_location, field)
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
                "parent",
            ]
        },
    )

    assert resp.status_code == status.HTTP_201_CREATED, resp.text

    expected = await Location.objects().get(Location.pk == resp.json()["location_ref"])
    assert expected is not None
    assert resp.json() == await sub_location_to_json(expected, default_payment_schemes)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_incorrect_parent_ref(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    await location_factory(merchant=merchant)
    sub_location = await location_factory(persist=False, merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{uuid4()}/sub_locations",
        json={
            field: getattr(sub_location, field)
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
                "parent",
            ]
        },
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


async def test_list_sub_locations(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    sub_locations = [
        await location_factory(merchant=merchant, parent=location) for _ in range(3)
    ]
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/sub_locations"
    )

    expected = []
    for sub_location in sub_locations:
        instance = await Location.objects().get(Location.pk == sub_location.pk)
        assert instance is not None
        expected.append(
            await sub_location_to_json(
                instance,
                default_payment_schemes,
            )
        )

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == expected


async def test_sub_location_details(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    sub_location = await location_factory(parent=location, merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/sub_locations/{sub_location.pk}"
    )

    assert resp.status_code == status.HTTP_200_OK, resp.text

    expected = await Location.objects().get(
        Location.pk == resp.json()["sub_location"]["location_ref"]
    )
    assert expected is not None
    assert resp.json() == await sub_location_to_json_detail(
        expected,
        location,
        default_payment_schemes,
    )


@pytest.mark.usefixtures("default_payment_schemes")
async def test_get_nonexistent_sub_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)

    await location_factory(parent=location, merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/sub_locations/{uuid4()}"
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


@pytest.mark.usefixtures("default_payment_schemes")
async def test_incorrect_location_ref_list_sub_locations(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    await location_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{uuid4()}/sub_locations"
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


async def test_edit_sub_locations(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    sub_location = await location_factory(parent=location, merchant=merchant)
    new_details = await location_factory(persist=False)
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/sub_locations/{sub_location.pk}",
        json={
            "name": new_details.name,
            "merchant_internal_id": new_details.merchant_internal_id,
            "is_physical_location": new_details.is_physical_location,
            "address_line_1": new_details.address_line_1,
            "address_line_2": new_details.address_line_2,
            "town_city": new_details.town_city,
            "county": new_details.county,
            "country": new_details.country,
            "postcode": new_details.postcode,
        },
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text

    expected = await Location.objects().get(Location.pk == sub_location.pk)
    assert expected is not None
    assert resp.json() == await sub_location_to_json_detail(
        expected,
        location,
        default_payment_schemes,
    )
    assert expected.name == new_details.name


@pytest.mark.usefixtures("default_payment_schemes")
async def test_edit_sub_locations_with_non_existent_id(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    await location_factory(parent=location, merchant=merchant)
    new_details = await location_factory(persist=False)
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/sub_locations/{uuid4()}",
        json={
            "name": new_details.name,
            "merchant_internal_id": new_details.merchant_internal_id,
            "is_physical_location": new_details.is_physical_location,
            "address_line_1": new_details.address_line_1,
            "address_line_2": new_details.address_line_2,
            "town_city": new_details.town_city,
            "county": new_details.county,
            "country": new_details.country,
            "postcode": new_details.postcode,
        },
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


async def test_reparent_sub_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    parent1 = await location_factory(merchant=merchant)
    parent2 = await location_factory(merchant=merchant)
    sub_location = await location_factory(parent=parent1, merchant=merchant)

    resp = test_client.patch(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{parent1.pk}/sub_locations/{sub_location.pk}",
        json={
            "parent_ref": str(parent2.pk),
        },
    )

    assert resp.status_code == status.HTTP_200_OK, resp.text

    expected = await Location.objects().get(Location.pk == sub_location.pk)
    assert expected is not None
    assert expected.parent == parent2.pk


async def test_reparent_sub_location_duplicate_location_id(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    parent1 = await location_factory(merchant=merchant)
    parent2 = await location_factory(merchant=merchant)
    sub_location = await location_factory(parent=parent1, merchant=merchant)

    resp = test_client.patch(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{parent1.pk}/sub_locations/{sub_location.pk}",
        json={
            "parent_ref": str(parent2.pk),
            "location_id": str(parent1.location_id),
        },
    )

    assert_is_uniqueness_error(resp, loc=["body", "location_id"])


async def test_remove_sub_location_parent(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    parent = await location_factory(merchant=merchant)
    sub_location = await location_factory(
        parent=parent, merchant=merchant, location_id=None
    )
    location_id = str(uuid4())

    resp = test_client.patch(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{parent.pk}/sub_locations/{sub_location.pk}",
        json={
            "parent_ref": None,
            "location_id": location_id,
        },
    )

    assert resp.status_code == status.HTTP_200_OK, resp.text

    expected = await Location.objects().get(Location.pk == sub_location.pk)
    assert expected is not None
    assert expected.parent is None
    assert expected.location_id == location_id


async def test_remove_sub_location_parent_no_location_id(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    parent = await location_factory(merchant=merchant)
    sub_location = await location_factory(
        parent=parent, merchant=merchant, location_id=None
    )

    resp = test_client.patch(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{parent.pk}/sub_locations/{sub_location.pk}",
        json={
            "parent_ref": None,
        },
    )

    assert_is_value_error(resp, loc=["body", "__root__"])


async def test_reparent_nonexistent_sub_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    parent1 = await location_factory(merchant=merchant)
    parent2 = await location_factory(merchant=merchant)
    await location_factory(parent=parent1, merchant=merchant)

    resp = test_client.patch(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{parent1.pk}/sub_locations/{uuid4()}",
        json={
            "parent_ref": str(parent2.pk),
        },
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


async def test_delete_sub_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    sub_locations = [
        await location_factory(merchant=merchant, parent=location),
        await location_factory(merchant=merchant, parent=location),
        await location_factory(merchant=merchant, parent=location),
    ]

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/deletion",
        json={"location_refs": [str(location.pk) for location in sub_locations]},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    assert resp.json() == [
        {
            "location_ref": str(sub_location.pk),
            "location_status": "deleted",
            "deletion_reason": None,
        }
        for sub_location in sub_locations
    ]


async def test_delete_sub_location_no_refs(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    await location_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/deletion",
        json={"location_refs": []},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    assert resp.json() == []
