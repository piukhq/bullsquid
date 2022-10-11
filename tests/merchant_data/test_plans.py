"""Test merchant data API endpoints that operate on plans."""

import random
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from qbert.tables import Job
from ward import test

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.db import get_plan
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from bullsquid.tasks import OffboardAndDeletePlan
from tests.fixtures import database, test_client
from tests.helpers import assert_is_not_found_error, assert_is_uniqueness_error
from tests.merchant_data.factories import (
    default_payment_schemes,
    identifier_factory,
    location_factory,
    merchant_factory,
    plan_factory,
    primary_mid_factory,
    secondary_mid_factory,
    secondary_mid_location_link_factory,
)


async def plan_to_json(plan: Plan, payment_schemes: list[PaymentScheme]) -> dict:
    """Convert a plan to its expected JSON representation."""
    merchant_count = await Merchant.count().where(Merchant.plan == plan)
    return {
        "plan_ref": str(plan.pk),
        "plan_status": plan.status,
        "plan_metadata": {
            "name": plan.name,
            "plan_id": plan.plan_id,
            "slug": plan.slug,
            "icon_url": plan.icon_url,
        },
        "plan_counts": {
            "merchants": merchant_count,
            "locations": 0,
            "payment_schemes": [
                {
                    "label": payment_scheme.label,
                    "scheme_code": payment_scheme.code,
                    "count": 0,
                }
                for payment_scheme in payment_schemes
            ],
        },
    }


@test("can list plans with no merchants")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    plans = [await plan_factory() for _ in range(3)]
    resp = test_client.get("/api/v1/plans")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [await plan_to_json(plan, payment_schemes) for plan in plans]


@test("can list plans with merchants")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    plans = [await plan_factory() for _ in range(3)]
    payment_schemes = await default_payment_schemes()
    for plan in plans:
        for _ in range(random.randint(1, 3)):
            await merchant_factory(plan=plan)

    resp = test_client.get("/api/v1/plans")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [await plan_to_json(plan, payment_schemes) for plan in plans]


@test("can get a plan's details")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    ps = await default_payment_schemes()
    resp = test_client.get(f"/api/v1/plans/{plan.pk}")
    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert resp.json() == await plan_to_json(plan, ps)


@test("can't get details of a non-existent plan")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    resp = test_client.get(f"/api/v1/plans/{uuid4()}")
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can create a plan")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    plan = await plan_factory(persist=False)
    resp = test_client.post(
        "/api/v1/plans",
        json={
            "name": plan.name,
            "plan_id": plan.plan_id,
            "slug": plan.slug,
            "icon_url": plan.icon_url,
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    plan = await get_plan(resp.json()["plan_ref"])
    assert resp.json() == await plan_to_json(plan, payment_schemes)


@test("can create a plan with a blank slug")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    plan = await plan_factory(persist=False, slug="")
    resp = test_client.post(
        "/api/v1/plans",
        json={
            "name": plan.name,
            "plan_id": plan.plan_id,
            "slug": plan.slug,
            "icon_url": plan.icon_url,
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    plan = await get_plan(resp.json()["plan_ref"])
    assert resp.json() == await plan_to_json(plan, payment_schemes)
    assert resp.json()["plan_metadata"]["slug"] is None


@test("unable to create a plan with a duplicate name")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    existing_plan = await plan_factory()
    new_plan = await plan_factory(persist=False)
    resp = test_client.post(
        "/api/v1/plans",
        json={
            "name": existing_plan.name,
            "plan_id": new_plan.plan_id,
            "slug": new_plan.slug,
            "icon_url": new_plan.icon_url,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "name"])


@test("unable to create a plan with a duplicate slug")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    existing_plan = await plan_factory()
    new_plan = await plan_factory(persist=False)
    resp = test_client.post(
        "/api/v1/plans",
        json={
            "name": new_plan.name,
            "plan_id": new_plan.plan_id,
            "slug": existing_plan.slug,
            "icon_url": new_plan.icon_url,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "slug"])


@test("unable to create a plan with a duplicate plan ID")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    existing_plan = await plan_factory()
    new_plan = await plan_factory(persist=False)
    resp = test_client.post(
        "/api/v1/plans",
        json={
            "name": new_plan.name,
            "plan_id": existing_plan.plan_id,
            "slug": new_plan.slug,
            "icon_url": new_plan.icon_url,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "plan_id"])


@test("can update an existing plan with new details")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    plan = await plan_factory()
    new_details = await plan_factory(persist=False)
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}",
        json={
            "name": new_details.name,
            "plan_id": new_details.plan_id,
            "slug": new_details.slug,
            "icon_url": new_details.icon_url,
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    plan = await get_plan(plan.pk)
    assert resp.json() == await plan_to_json(plan, payment_schemes)
    assert plan.name == new_details.name
    assert plan.plan_id == new_details.plan_id
    assert plan.slug == new_details.slug
    assert plan.icon_url == new_details.icon_url


@test("updating a non-existent plan returns a ref error")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    resp = test_client.put(
        f"/api/v1/plans/{uuid4()}",
        json={
            "name": "New name",
        },
    )
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("updating a plan with an existing name returns a uniqueness error")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plans = [await plan_factory() for _ in range(3)]
    resp = test_client.put(
        f"/api/v1/plans/{plans[0].pk}",
        json={
            "name": plans[1].name,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "name"])


@test("updating a plan with an existing slug returns a uniqueness error")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plans = [await plan_factory() for _ in range(3)]
    resp = test_client.put(
        f"/api/v1/plans/{plans[0].pk}",
        json={
            "name": plans[0].name,
            "slug": plans[1].slug,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "slug"])


@test("updating a plan with an existing plan ID returns a uniqueness error")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plans = [await plan_factory() for _ in range(3)]
    resp = test_client.put(
        f"/api/v1/plans/{plans[0].pk}",
        json={
            "name": plans[0].name,
            "plan_id": plans[1].plan_id,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "plan_id"])


@test("a plan with no dependent resources is immediately deleted")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    resp = test_client.delete(f"/api/v1/plans/{plan.pk}")
    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text


@test("a plan with no onboarded resources is immediately deleted")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )
    secondary_mid = await secondary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )
    identifier = await identifier_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )
    location = await location_factory(merchant=merchant)
    secondary_mid_location_link = await secondary_mid_location_link_factory(
        secondary_mid=secondary_mid, location=location
    )

    resp = test_client.delete(f"/api/v1/plans/{plan.pk}")

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {"plan_status": "deleted"}

    plan = await Plan.select(Plan.status).where(Plan.pk == plan.pk).first()
    merchant = (
        await Merchant.select(Merchant.status).where(Merchant.pk == merchant.pk).first()
    )
    primary_mid = (
        await PrimaryMID.select(PrimaryMID.status)
        .where(PrimaryMID.pk == primary_mid.pk)
        .first()
    )
    secondary_mid = (
        await SecondaryMID.select(SecondaryMID.status)
        .where(SecondaryMID.pk == secondary_mid.pk)
        .first()
    )
    identifier = (
        await Identifier.select(Identifier.status)
        .where(Identifier.pk == identifier.pk)
        .first()
    )
    location = (
        await Location.select(Location.status).where(Location.pk == location.pk).first()
    )

    assert plan["status"] == ResourceStatus.DELETED
    assert merchant["status"] == ResourceStatus.DELETED
    assert primary_mid["status"] == ResourceStatus.DELETED
    assert secondary_mid["status"] == ResourceStatus.DELETED
    assert identifier["status"] == ResourceStatus.DELETED
    assert location["status"] == ResourceStatus.DELETED
    assert not await SecondaryMIDLocationLink.exists().where(
        SecondaryMIDLocationLink.pk == secondary_mid_location_link.pk
    )


@test("a plan with onboarded resources is set to pending deletion")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    await primary_mid_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)
    await secondary_mid_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)
    await identifier_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)

    resp = test_client.delete(f"/api/v1/plans/{plan.pk}")

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {"plan_status": "pending_deletion"}

    assert await Job.exists().where(
        Job.message_type == OffboardAndDeletePlan.__name__,
        Job.message == OffboardAndDeletePlan(plan_ref=plan.pk).dict(),
    )

    plan = await Plan.select(Plan.status).where(Plan.pk == plan.pk).first()
    assert plan["status"] == ResourceStatus.PENDING_DELETION


@test("deleting a non-existent plan returns a ref error")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    resp = test_client.delete(f"/api/v1/plans/{uuid4()}")
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])
