from typing import Any
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from tests.helpers import (
    Factory,
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_uniqueness_error,
    assert_is_value_error,
)


async def location_to_json(
    location: Location,
    *,
    is_sub_location: bool = False,
    include_sub_locations: bool = False,
) -> dict:
    """Converts a location to its expected JSON representation."""
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
    }

    if not is_sub_location:
        data["location_metadata"]["location_id"] = location.location_id
        data["sub_locations"] = (
            [
                await location_to_json(sub_location, is_sub_location=True)
                for sub_location in await Location.objects().where(
                    Location.parent == location.pk
                )
            ]
            if include_sub_locations
            else None
        )

    return data


async def location_to_json_detail(location: Location) -> dict:
    """Converts a location to its expected JSON representation."""
    if location.parent:
        raise ValueError("sub-location passed to location json helper")

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
    }


def test_title_name_only() -> None:
    location = Location(name="test location")
    assert location.display_text == "test location"


def test_title_mixed_fields() -> None:
    location = Location(name="test location", town_city="test town")
    assert location.display_text == "test location, test town"


def test_title_all_fields() -> None:
    location = Location(
        name="test location",
        address_line_1="1 test street",
        town_city="test town",
        postcode="T35T L0C",
    )
    assert location.display_text == "test location, 1 test street, test town, T35T L0C"


async def test_list(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    locations = [await location_factory() for _ in range(3)]
    {
        location.location_id: {"visa": 0, "mastercard": 0, "amex": 0}
        for location in locations
    }
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations")

    assert resp.status_code == status.HTTP_200_OK
    expected = await Location.objects().get(Location.pk == location.pk)
    assert expected is not None
    assert resp.json() == [await location_to_json(expected)]


async def test_list_with_sub_locations(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    await location_factory(merchant=merchant, parent=location)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations?include_sub_locations=true"
    )

    assert resp.status_code == status.HTTP_200_OK

    expected = await Location.objects().get(Location.pk == location.pk)
    assert expected is not None

    assert resp.json() == [await location_to_json(expected, include_sub_locations=True)]


async def test_list_with_invalid_plan(
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()

    resp = test_client.get(f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations")

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_list_with_invalid_merchant(
    plan_factory: Factory[Plan],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/locations")

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def testlist_exclude_secondary_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_factory: Factory[SecondaryMID],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
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
        await secondary_mid_location_link_factory(
            location=location, secondary_mid=secondary_mid
        )

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        params={"exclude_secondary_mid": str(secondary_mid.pk)},
    )

    assert resp.status_code == 200

    expected = await Location.objects().where(
        Location.pk.is_in([location.pk for location in locations[-2:]])
    )
    assert resp.json() == [await location_to_json(location) for location in expected]


async def test_list_exclude_unlinked_secondary_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    location = await location_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        params={"exclude_secondary_mid": str(secondary_mid.pk)},
    )

    assert resp.status_code == 200

    expected = await Location.objects().get(Location.pk == location.pk)
    assert expected is not None
    assert resp.json() == [await location_to_json(expected)]


async def test_list_exclude_nonexistent_secondary_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        params={"exclude_secondary_mid": str(uuid4())},
    )

    assert_is_not_found_error(resp, loc=["query", "exclude_secondary_mid"])


async def test_list_exclude_secondary_mid_from_wrong_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory()

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations",
        params={"exclude_secondary_mid": str(secondary_mid.pk)},
    )

    assert_is_not_found_error(resp, loc=["query", "exclude_secondary_mid"])


async def test_details(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}"
    )

    assert resp.status_code == status.HTTP_200_OK

    expected = await Location.objects().get(Location.pk == location.pk)
    assert expected is not None

    assert resp.json() == await location_to_json_detail(expected)


async def test_details_invalid_location_ref(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{uuid4()}"
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


async def test_details_invalid_merchant_ref(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/locations/{location.pk}"
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_details_invalid_plan_ref(
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations/{location.pk}"
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_create(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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

    expected = await Location.objects().get(Location.pk == resp.json()["location_ref"])
    assert expected is not None
    assert resp.json() == await location_to_json(expected)


async def test_create_withoutnexistent_plan(
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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


async def test_create_withoutnexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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


async def test_create_without_location_id(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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


async def test_create_without_name(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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


async def test_create_without_is_physical_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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


async def test_create_with_duplication_location_id(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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

    assert_is_uniqueness_error(resp, loc=["body", "plan_ref"])


async def test_create_physical_location_without_address_line_1(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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


async def test_create_physical_location_without_postcode(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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


async def test_delete(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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
        {
            "location_ref": str(location.pk),
            "location_status": "deleted",
            "reason": None,
        }
        for location in locations
    ]


async def test_delete_zero_refs(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/deletion",
        json={"location_refs": []},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    assert resp.json() == []


async def test_delete_primary_mid_link(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory(merchant=merchant, location=location)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/deletion",
        json={"location_refs": [str(location.pk)]},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED

    expected = await PrimaryMID.objects().get(PrimaryMID.pk == primary_mid.pk)
    assert expected is not None
    assert expected.location is None


async def test_delete_secondary_mid_link(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    await secondary_mid_location_link_factory(location=location)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/deletion",
        json={"location_refs": [str(location.pk)]},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED

    assert not await SecondaryMIDLocationLink.exists().where(
        SecondaryMIDLocationLink.location == location
    )


async def test_delete_with_nonexistent_plan(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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


async def test_delete_with_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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


async def test_delete_nonexistent_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/deletion",
        json={"location_refs": [str(uuid4()) for _ in range(3)]},
    )

    assert_is_not_found_error(resp, loc=["body", "location_refs"])


async def test_associate_primary_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/mids",
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


async def test_associate_primary_mid_incorrect_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory()

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/mids",
        json={"mid_refs": [str(primary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["body", "mid_ref"])


async def test_associate_primary_mid_nonexistent_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{uuid4()}/mids",
        json={"mid_refs": [str(primary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


async def test_associate_primary_mid_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/locations/{location.pk}/mids",
        json={"mid_refs": [str(primary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_associate_primary_mid_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations/{location.pk}/mids",
        json={"mid_refs": [str(primary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_associate_secondary_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/secondary_mid_location_links",
        json={"secondary_mid_refs": [str(secondary_mid.pk)]},
    )

    assert resp.status_code == status.HTTP_201_CREATED

    link = (
        await SecondaryMIDLocationLink.select(SecondaryMIDLocationLink.pk)
        .where(
            SecondaryMIDLocationLink.secondary_mid == secondary_mid,
            SecondaryMIDLocationLink.location == location,
        )
        .first()
    )
    assert link is not None
    assert resp.json() == [
        {
            "link_ref": str(link["pk"]),
            "secondary_mid_ref": str(secondary_mid.pk),
            "payment_scheme_slug": secondary_mid.payment_scheme.slug,
            "secondary_mid_value": secondary_mid.secondary_mid,
        }
    ]


async def test_associate_secondary_mid_wrong_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory()

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/secondary_mid_location_links",
        json={"secondary_mid_refs": [str(secondary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["body", "secondary_mid_ref"])


async def test_associate_secondary_mid_nonexistent_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{uuid4()}/secondary_mid_location_links",
        json={"secondary_mid_refs": [str(secondary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


async def test_associate_secondary_mid_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/locations/{location.pk}/secondary_mid_location_links",
        json={"secondary_mid_refs": [str(secondary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_associate_secondary_mid_nonexistent_plan(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations/{location.pk}/secondary_mid_location_links",
        json={"secondary_mid_refs": [str(secondary_mid.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_associate_secondary_mid_twice(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    """
    We don't actually need to check the database in this test - the unique
    constraint will prevent the insertion of a second association.
    """
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    location = await location_factory(merchant=merchant)

    url = (
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}"
        f"/locations/{location.pk}/secondary_mid_location_links"
    )
    json = {"secondary_mid_refs": [str(secondary_mid.pk)]}

    resp1 = test_client.post(url, json=json)
    assert resp1.status_code == status.HTTP_201_CREATED

    resp2 = test_client.post(url, json=json)
    assert resp2.status_code == status.HTTP_200_OK

    assert resp1.json()[0]["link_ref"] == resp2.json()[0]["link_ref"]


async def test_available_mids(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    location_2 = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory(merchant=merchant, location=location_2)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/available_mids",
    )

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [
        {
            "mid": {
                "mid_ref": str(primary_mid.pk),
                "payment_scheme_slug": primary_mid.payment_scheme.slug,
                "mid_value": primary_mid.mid,
            },
            "location_link": {
                "location_ref": str(location_2.pk),
                "location_title": location_2.display_text,
            },
        }
    ]


async def test_available_mids_invalid_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    await location_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{uuid4()}/available_mids",
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


async def test_available_mids_invalid_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/locations/{location.pk}/available_mids",
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_available_mids_invalid_plan_ref(
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations/{location.pk}/available_mids",
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_unlinked_available_mids(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory(merchant=merchant, location=None)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/available_mids",
    )

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [
        {
            "mid": {
                "mid_ref": str(primary_mid.pk),
                "payment_scheme_slug": primary_mid.payment_scheme.slug,
                "mid_value": primary_mid.mid,
            },
            "location_link": None,
        }
    ]


async def test_associated_mids(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory(merchant=merchant, location=location)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/mids"
    )

    assert resp.status_code == status.HTTP_200_OK

    assert resp.json() == [
        {
            "mid_ref": str(primary_mid.pk),
            "payment_scheme_slug": primary_mid.payment_scheme.slug,
            "mid_value": primary_mid.mid,
        }
    ]


async def test_associated_mids_nonexistent_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    await primary_mid_factory(merchant=merchant, location=location)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{uuid4()}/mids"
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


async def test_associated_mids_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    await primary_mid_factory(merchant=merchant, location=location)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/locations/{location.pk}/mids"
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_assocated_mids_nonexistent_plan(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    await primary_mid_factory(merchant=merchant, location=location)

    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations/{location.pk}/mids"
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_associated_secondary_mids(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_factory: Factory[SecondaryMID],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    link = await secondary_mid_location_link_factory(
        location=location, secondary_mid=secondary_mid
    )

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}/secondary_mid_location_links"
    )

    assert resp.status_code == status.HTTP_200_OK

    assert resp.json() == [
        {
            "link_ref": str(link.pk),
            "secondary_mid_ref": str(secondary_mid.pk),
            "payment_scheme_slug": secondary_mid.payment_scheme.slug,
            "secondary_mid_value": secondary_mid.secondary_mid,
        }
    ]


async def test_associated_secondary_mids_nonexistent_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_factory: Factory[SecondaryMID],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    await secondary_mid_location_link_factory(
        location=location, secondary_mid=secondary_mid
    )

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{uuid4()}/secondary_mid_location_links"
    )

    assert_is_not_found_error(resp, loc=["path", "location_ref"])


async def test_associated_secondary_mids_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_factory: Factory[SecondaryMID],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    await secondary_mid_location_link_factory(
        location=location, secondary_mid=secondary_mid
    )

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/locations/{location.pk}/secondary_mid_location_links"
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_associated_secondary_mid_nonexistent_plan(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_factory: Factory[SecondaryMID],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    await secondary_mid_location_link_factory(
        location=location, secondary_mid=secondary_mid
    )

    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/locations/{location.pk}/secondary_mid_location_links"
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_edit_locations(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    new_details = await location_factory(persist=False)
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}",
        json={
            "name": new_details.name,
            "location_id": new_details.location_id,
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

    expected = await Location.objects().get(Location.pk == location.pk)
    assert expected is not None
    assert resp.json() == await location_to_json_detail(expected)
    assert expected.name == new_details.name


async def test_edit_location_with_non_existent_id(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    new_details = await location_factory(persist=False)
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{uuid4()}",
        json={
            "name": new_details.name,
            "location_id": new_details.location_id,
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


async def test_location_mid_counts(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    await primary_mid_factory(merchant=merchant, location=location)
    await primary_mid_factory(merchant=merchant, location=location)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["linked_mids_count"] == 2


async def test_location_secondary_mid_counts(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_factory: Factory[SecondaryMID],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    await secondary_mid_location_link_factory(
        location=location, secondary_mid=secondary_mid
    )

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/locations/{location.pk}",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["linked_secondary_mids_count"] == 1
