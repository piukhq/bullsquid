"""Test merchant data API endpoints that operate on merchants."""

from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from qbert.tables import Job
from ward import raises, test

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from bullsquid.tasks import OffboardAndDeleteMerchant
from tests.fixtures import database, test_client
from tests.helpers import (
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_uniqueness_error,
    assert_is_value_error,
)
from tests.merchant_data.factories import (
    default_payment_schemes,
    identifier_factory,
    merchant_factory,
    plan_factory,
    primary_mid_factory,
    secondary_mid_factory,
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    plan = await plan_factory()
    merchants = [
        await merchant_factory(plan=plan),
        await merchant_factory(plan=plan),
        await merchant_factory(plan=plan),
    ]

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [
        merchant_overview_json(merchant, payment_schemes) for merchant in merchants
    ]


@test("listing merchants on a non-existent plan returns a 404")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    resp = test_client.get(f"/api/v1/plans/{uuid4()}/merchants")
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can get merchant details")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == merchant_detail_json(merchant, plan)


@test("getting merchant details from a non-existent plan returns a 404")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.get(f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}")
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("getting details from a non-existent merchant returns a 404")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}")
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can create a merchant")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    existing_merchant = await merchant_factory()
    new_merchant = await merchant_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{existing_merchant.plan}/merchants",
        json={
            "name": existing_merchant.name,
            "icon_url": new_merchant.icon_url,
            "location_label": new_merchant.location_label,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "name"])


@test("unable to create a merchant on a non-existent plan")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    new_merchant = await merchant_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants",
        json={
            "name": new_merchant.name,
            "icon_url": new_merchant.icon_url,
            "location_label": new_merchant.location_label,
        },
    )
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("unable to create a merchant with a blank name instead of null")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants",
        json={
            "name": "",
            "icon_url": merchant.icon_url,
            "location_label": merchant.location_label,
        },
    )
    assert_is_value_error(resp, loc=["body", "name"])


@test("unable to create a merchant with a blank location label instead of null")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants",
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
) -> None:
    merchant = await merchant_factory()
    new_details = await merchant_factory(persist=False)
    resp = test_client.put(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}",
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
) -> None:
    merchant = await merchant_factory()
    resp = test_client.put(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}",
        json={"location_label": "new location"},
    )
    assert_is_missing_field_error(resp, loc=["body", "name"])


@test("updating a merchant requires a location label")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.put(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}",
        json={"name": "new name"},
    )
    assert_is_missing_field_error(resp, loc=["body", "location_label"])


@test("updating a non-existent merchant returns a ref error")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}",
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
) -> None:
    merchant = await merchant_factory()
    resp = test_client.put(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}",
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
) -> None:
    plan = await plan_factory()
    merchants = [
        await merchant_factory(plan=plan),
        await merchant_factory(),
    ]
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{merchants[0].pk}",
        json={
            "name": merchants[1].name,
            "location_label": "new location",
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "name"])


@test("deleted merchants are not listed")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    payment_schemes = await default_payment_schemes()

    # create a deleted merchant that shouldn't be in the response
    await merchant_factory(status=ResourceStatus.DELETED)

    resp = test_client.get(f"/api/v1/plans/{merchant.plan}/merchants")

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [merchant_overview_json(merchant, payment_schemes)]


@test("a merchant with no onboarded resources is immediately deleted")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    primary_mid = await primary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )
    secondary_mid = await secondary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )
    identifier = await identifier_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )

    resp = test_client.delete(f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}")

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {"merchant_status": "deleted"}

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

    assert merchant["status"] == ResourceStatus.DELETED
    assert primary_mid["status"] == ResourceStatus.DELETED
    assert secondary_mid["status"] == ResourceStatus.DELETED
    assert identifier["status"] == ResourceStatus.DELETED


@test("a merchant with onboarded resources is set to pending deletion")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    await primary_mid_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)
    await secondary_mid_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)
    await identifier_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)

    resp = test_client.delete(f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}")

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {"merchant_status": "pending_deletion"}

    assert await Job.exists().where(
        Job.message_type == OffboardAndDeleteMerchant.__name__,
        Job.message == OffboardAndDeleteMerchant(merchant_ref=merchant.pk).dict(),
    )

    merchant = (
        await Merchant.select(Merchant.status).where(Merchant.pk == merchant.pk).first()
    )
    assert merchant["status"] == ResourceStatus.PENDING_DELETION


@test("deleting a non-existent merchant returns a ref error")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    resp = test_client.delete(f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}")
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("deleting a merchant on a non-existent plan returns a ref error")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.delete(f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}")
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("get_merchant fails if validate_plan is true and plan_ref is null")
async def _() -> None:
    with raises(ValueError) as ex:
        await get_merchant(uuid4(), plan_ref=None)
    assert ex.raised.args[0] == "validate_plan cannot be true if plan_ref is null"
