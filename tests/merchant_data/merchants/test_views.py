"""Test merchant data API endpoints that operate on merchants."""

from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from ward import skip, test

from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from tests.fixtures import auth_header, database, test_client
from tests.helpers import (
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_uniqueness_error,
    assert_is_value_error,
)
from tests.merchant_data.factories import (
    merchant,
    merchant_factory,
    payment_schemes,
    plan,
    plan_factory,
    three_merchants,
)


def merchant_overview_json(
    merchant: Merchant, payment_schemes: list[PaymentScheme]
) -> dict:
    """Convert a merchant to its expected list JSON representation."""
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


def merchant_detail_json(merchant: Merchant, plan: Plan) -> dict:
    """Convert a merchant to its expected detail JSON representation."""
    return {
        "merchant_ref": str(merchant.pk),
        "plan_metadata": {
            "name": plan.name,
            "plan_id": plan.plan_id,
            "slug": plan.slug,
            "icon_url": plan.icon_url,
        },
        "merchant_metadata": {
            "name": merchant.name,
            "icon_url": merchant.icon_url,
            "location_label": merchant.location_label,
        },
    }


@test("can list merchants")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plan: Plan = plan,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    merchants = [
        await merchant_factory(plan=plan),
        await merchant_factory(plan=plan),
        await merchant_factory(plan=plan),
    ]

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants", headers=auth_header)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [
        merchant_overview_json(merchant, payment_schemes) for merchant in merchants
    ]


@test("listing merchants on a non-existent plan returns a 404")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    resp = test_client.get(f"/api/v1/plans/{uuid4()}/merchants", headers=auth_header)
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can get merchant details")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}", headers=auth_header
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == merchant_detail_json(merchant, plan)


@test("getting merchant details from a non-existent plan returns a 404")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}", headers=auth_header
    )
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("getting details from a non-existent merchant returns a 404")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plan: Plan = plan,
) -> None:
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}", headers=auth_header
    )
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


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
    assert resp.status_code == status.HTTP_201_CREATED
    merchant = await get_merchant(resp.json()["merchant_ref"], plan_ref=plan.pk)
    assert resp.json() == merchant_overview_json(merchant, payment_schemes)


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
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    merchant = await merchant_factory()
    new_details = await merchant_factory(persist=False)
    resp = test_client.put(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}",
        headers=auth_header,
        json={
            "name": new_details.name,
            "icon_url": new_details.icon_url,
            "location_label": new_details.location_label,
        },
    )
    assert resp.status_code == status.HTTP_200_OK

    merchant = await Merchant.objects().get(Merchant.pk == merchant.pk)
    assert resp.json() == merchant_overview_json(
        merchant, await PaymentScheme.objects()
    )
    assert merchant.name == new_details.name
    assert merchant.icon_url == new_details.icon_url
    assert merchant.location_label == new_details.location_label


@test("updating a merchant requires a name")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.put(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}",
        headers=auth_header,
        json={"location_label": "new location"},
    )
    assert_is_missing_field_error(resp, loc=["body", "name"])


@test("updating a merchant requires a location label")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.put(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}",
        headers=auth_header,
        json={"name": "new name"},
    )
    assert_is_missing_field_error(resp, loc=["body", "location_label"])


@test("updating a non-existent merchant returns a ref error")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    plan = await plan_factory()
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}",
        headers=auth_header,
        json={
            "name": "new name",
            "location_label": "new location",
        },
    )
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("updating a merchant on a non-existent plan returns a ref error")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.put(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}",
        headers=auth_header,
        json={
            "name": "new name",
            "location_label": "new location",
        },
    )
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("updating a merchant with an existing name returns a uniqueness error")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    plan = await plan_factory()
    merchants = [
        await merchant_factory(plan=plan),
        await merchant_factory(),
    ]
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{merchants[0].pk}",
        headers=auth_header,
        json={
            "name": merchants[1].name,
            "location_label": "new location",
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "name"])
