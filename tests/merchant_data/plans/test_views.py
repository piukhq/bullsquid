"""Test merchant data API endpoints that operate on plans."""

import random
from uuid import uuid4

from fastapi.testclient import TestClient
from ward import test

from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.db import get_plan
from bullsquid.merchant_data.plans.tables import Plan
from tests.factories import (
    merchant_factory,
    payment_schemes,
    plan,
    plan_factory,
    three_plans,
)
from tests.fixtures import auth_header, database, test_client
from tests.helpers import (
    assert_is_not_found_error,
    assert_is_uniqueness_error,
    assert_is_value_error,
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
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plans: list[dict] = three_plans,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    resp = test_client.get("/api/v1/plans", headers=auth_header)
    assert resp.ok, resp.json()
    assert resp.json() == [await plan_to_json(plan, payment_schemes) for plan in plans]


@test("can list plans with merchants")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plans: list[dict] = three_plans,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    for plan in plans:
        for _ in range(random.randint(1, 3)):
            await merchant_factory(plan=plan)

    resp = test_client.get("/api/v1/plans", headers=auth_header)
    assert resp.ok, resp.json()
    assert resp.json() == [await plan_to_json(plan, payment_schemes) for plan in plans]


@test("can create a plan")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    plan = await plan_factory(persist=False)
    resp = test_client.post(
        "/api/v1/plans",
        headers=auth_header,
        json={
            "name": plan.name,
            "plan_id": plan.plan_id,
            "slug": plan.slug,
            "icon_url": plan.icon_url,
        },
    )
    assert resp.ok, resp.json()
    plan = await get_plan(resp.json()["plan_ref"])
    assert resp.json() == await plan_to_json(plan, payment_schemes)


@test("unable to create a plan with a duplicate name")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    existing_plan: Plan = plan,
) -> None:
    new_plan = await plan_factory(persist=False)
    resp = test_client.post(
        "/api/v1/plans",
        headers=auth_header,
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
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    existing_plan: Plan = plan,
) -> None:
    new_plan = await plan_factory(persist=False)
    resp = test_client.post(
        "/api/v1/plans",
        headers=auth_header,
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
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    existing_plan: Plan = plan,
) -> None:
    new_plan = await plan_factory(persist=False)
    resp = test_client.post(
        "/api/v1/plans",
        headers=auth_header,
        json={
            "name": new_plan.name,
            "plan_id": existing_plan.plan_id,
            "slug": new_plan.slug,
            "icon_url": new_plan.icon_url,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "plan_id"])


@test("unable to create a plan with blank name instead of null")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    plan = await plan_factory(persist=False)
    resp = test_client.post(
        "/api/v1/plans",
        headers=auth_header,
        json={
            "name": "",
            "plan_id": plan.plan_id,
            "slug": plan.slug,
            "icon_url": plan.icon_url,
        },
    )
    assert_is_value_error(resp, loc=["body", "name"])


@test("unable to create a plan with blank slug instead of null")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    plan = await plan_factory(persist=False)
    resp = test_client.post(
        "/api/v1/plans",
        headers=auth_header,
        json={
            "name": plan.name,
            "plan_id": plan.plan_id,
            "slug": "",
            "icon_url": plan.icon_url,
        },
    )
    assert_is_value_error(resp, loc=["body", "slug"])


@test("can update an existing plan with new details")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plan: Plan = plan,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    new_details = await plan_factory(persist=False)
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}",
        headers=auth_header,
        json={
            "name": new_details.name,
            "plan_id": new_details.plan_id,
            "slug": new_details.slug,
            "icon_url": new_details.icon_url,
        },
    )
    assert resp.ok, resp.json()
    plan = await get_plan(plan.pk)
    assert resp.json() == await plan_to_json(plan, payment_schemes)
    assert plan.name == new_details.name
    assert plan.plan_id == new_details.plan_id
    assert plan.slug == new_details.slug
    assert plan.icon_url == new_details.icon_url


@test("updating a non-existent plan returns a ref error")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    resp = test_client.put(
        f"/api/v1/plans/{uuid4()}",
        headers=auth_header,
        json={
            "name": "New name",
        },
    )
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("updating a plan with an existing name returns a uniqueness error")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plans: list[Plan] = three_plans,
) -> None:
    resp = test_client.put(
        f"/api/v1/plans/{plans[0].pk}",
        headers=auth_header,
        json={
            "name": plans[1].name,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "name"])


@test("updating a plan with an existing slug returns a uniqueness error")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plans: list[Plan] = three_plans,
) -> None:
    resp = test_client.put(
        f"/api/v1/plans/{plans[0].pk}",
        headers=auth_header,
        json={
            "name": plans[0].name,
            "slug": plans[1].slug,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "slug"])


@test("updating a plan with an existing plan ID returns a uniqueness error")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plans: list[Plan] = three_plans,
) -> None:
    resp = test_client.put(
        f"/api/v1/plans/{plans[0].pk}",
        headers=auth_header,
        json={
            "name": plans[0].name,
            "plan_id": plans[1].plan_id,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "plan_id"])


@test("unable to update a plan with a blank name instead of null")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plan: Plan = plan,
) -> None:
    new_details = await plan_factory(persist=False)
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}",
        headers=auth_header,
        json={
            "name": "",
            "plan_id": new_details.plan_id,
            "slug": new_details.slug,
            "icon_url": new_details.icon_url,
        },
    )
    assert_is_value_error(resp, loc=["body", "name"])


@test("unable to update a plan with a blank slug instead of null")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plan: Plan = plan,
) -> None:
    new_details = await plan_factory(persist=False)
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}",
        headers=auth_header,
        json={
            "name": new_details.name,
            "plan_id": new_details.plan_id,
            "slug": "",
            "icon_url": new_details.icon_url,
        },
    )
    assert_is_value_error(resp, loc=["body", "slug"])
