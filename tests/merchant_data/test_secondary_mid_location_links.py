from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from ward import test

from tests.fixtures import database, test_client
from tests.helpers import assert_is_not_found_error
from tests.merchant_data.factories import (
    location_factory,
    merchant_factory,
    plan_factory,
    secondary_mid_factory,
    secondary_mid_location_link_factory,
)


@test("can delete a secondary MID location link")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
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


@test("can't delete a secondary MID location link that doesn't exist")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
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


@test("can't delete a secondary MID location link from a different merchant")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
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


@test("can't delete a secondary MID location link on a plan that doesn't exist")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
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


@test("can't delete a secondary MID location link on a merchant that doesn't exist")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
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
