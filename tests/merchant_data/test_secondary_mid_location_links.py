from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from tests.helpers import Factory, assert_is_not_found_error


async def test_delete(
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

    resp = test_client.delete(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mid_location_links/{link.pk}"
    )

    assert resp.status_code == status.HTTP_204_NO_CONTENT, resp.text


async def test_delete_nonexistent_link(
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

    resp = test_client.delete(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mid_location_links/{uuid4()}"
    )

    assert_is_not_found_error(resp, loc=["path", "link_ref"])


async def test_delete_with_wrong_merchant(
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

    other_merchant = await merchant_factory(plan=plan)

    resp = test_client.delete(
        f"/api/v1/plans/{plan.pk}/merchants/{other_merchant.pk}/secondary_mid_location_links/{uuid4()}"
    )

    assert_is_not_found_error(resp, loc=["path", "link_ref"])


async def test_delete_with_nonexistent_plan(
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

    resp = test_client.delete(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/secondary_mid_location_links/{uuid4()}"
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_delete_with_nonexistent_merchant(
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

    resp = test_client.delete(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/secondary_mid_location_links/{uuid4()}"
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])
