"""Test merchant data API endpoints that operate on merchants."""

from uuid import uuid4

from fastapi.testclient import TestClient
from ward import skip, test

from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from tests.factories import (
    merchant,
    merchant_factory,
    payment_schemes,
    plan,
    three_merchants,
)
from tests.fixtures import auth_header, database, test_client
from tests.helpers import (
    assert_is_not_found_error,
    assert_is_uniqueness_error,
    assert_is_value_error,
)


def merchant_to_json(merchant: Merchant, payment_schemes: list[PaymentScheme]) -> dict:
    """Convert a merchant to its expected JSON representation."""
    return {
        "merchant_ref": str(merchant.pk),
        "merchant_status": merchant.status,
        "merchant_metadata": {
            "name": merchant.name,
            "icon_url": merchant.icon_url,
            "location_label": merchant.location_label,
        },
        "merchant_counts": {
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


@test("can list merchants")
@skip("not yet implemented")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchants: list[dict] = three_merchants,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    resp = test_client.get("/api/v1/merchants", headers=auth_header)
    assert resp.ok, resp.json()
    assert resp.json() == [
        merchant_to_json(merchant, payment_schemes) for merchant in merchants
    ]


@test("can create a merchant")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    payment_schemes: list[PaymentScheme] = payment_schemes,
    plan: Plan = plan,
) -> None:
    merchant = await merchant_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants",
        headers=auth_header,
        json={
            "name": merchant.name,
            "icon_url": merchant.icon_url,
            "location_label": merchant.location_label,
        },
    )
    assert resp.ok, resp.json()
    merchant = await get_merchant(resp.json()["merchant_ref"], plan_ref=plan.pk)
    assert resp.json() == merchant_to_json(merchant, payment_schemes)


@test("unable to create a merchant with a duplicate name")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    existing_merchant: Merchant = merchant,
) -> None:
    new_merchant = await merchant_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{existing_merchant.plan}/merchants",
        headers=auth_header,
        json={
            "name": existing_merchant.name,
            "icon_url": new_merchant.icon_url,
            "location_label": new_merchant.location_label,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "name"])


@test("unable to create a merchant on a non-existant plan")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    new_merchant = await merchant_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants",
        headers=auth_header,
        json={
            "name": new_merchant.name,
            "icon_url": new_merchant.icon_url,
            "location_label": new_merchant.location_label,
        },
    )
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("unable to create a merchant with a blank name instead of null")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plan: Plan = plan,
) -> None:
    merchant = await merchant_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants",
        headers=auth_header,
        json={
            "name": "",
            "icon_url": merchant.icon_url,
            "location_label": merchant.location_label,
        },
    )
    assert_is_value_error(resp, loc=["body", "name"])


@test("unable to create a merchant with a blank location label instead of null")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plan: Plan = plan,
) -> None:
    merchant = await merchant_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants",
        headers=auth_header,
        json={
            "name": merchant.name,
            "icon_url": merchant.icon_url,
            "location_label": "",
        },
    )
    assert_is_value_error(resp, loc=["body", "location_label"])


@test("can update an existing merchant with new details")
@skip("not yet implemented")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    new_details = await merchant_factory(persist=False)
    resp = test_client.put(
        f"/api/v1/merchants/{merchant.pk}",
        headers=auth_header,
        json={
            "name": new_details.name,
            "merchant_id": new_details.merchant_id,
            "slug": new_details.slug,
            "icon_url": new_details.icon_url,
        },
    )
    assert resp.ok, resp.json()
    merchant = await get_merchant(merchant.pk, plan_ref=merchant.plan)
    assert resp.json() == merchant_to_json(merchant, payment_schemes)
    assert merchant.name == new_details.name
    assert merchant.merchant_id == new_details.merchant_id
    assert merchant.slug == new_details.slug
    assert merchant.icon_url == new_details.icon_url


@test("updating a non-existent merchant returns a ref error")
@skip("not yet implemented")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    resp = test_client.put(
        f"/api/v1/merchants/{uuid4()}",
        headers=auth_header,
        json={
            "name": "New name",
        },
    )
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("updating a merchant with an existing name returns a uniqueness error")
@skip("not yet implemented")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchants: list[Merchant] = three_merchants,
) -> None:
    resp = test_client.put(
        f"/api/v1/merchants/{merchants[0].pk}",
        headers=auth_header,
        json={
            "name": merchants[1].name,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "name"])
