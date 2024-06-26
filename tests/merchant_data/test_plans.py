"""Test merchant data API endpoints that operate on plans."""

import random
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from qbert.tables import Job

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.db import get_plan
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.psimis.tables import PSIMI
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from bullsquid.merchant_data.tasks import OffboardAndDeletePlan
from tests.helpers import Factory, assert_is_not_found_error, assert_is_uniqueness_error


async def plan_overview_json(
    plan: Plan,
    payment_schemes: list[PaymentScheme],
    merchant_refs: list[str],
    locations: int = 0,
    visa_identifiers: int = 0,
    mastercard_identifiers: int = 0,
    amex_identifiers: int = 0,
) -> dict:
    """Convert a plan to its expected JSON representation."""

    return {
        "plan_ref": str(plan.pk),
        "plan_status": ResourceStatus(plan.status).value,
        "plan_metadata": {
            "name": plan.name,
            "plan_id": plan.plan_id,
            "slug": plan.slug,
            "icon_url": plan.icon_url,
        },
        "plan_counts": {
            "merchants": len(merchant_refs),
            "locations": locations,
            "payment_schemes": [
                {
                    "slug": payment_scheme.slug,
                    "count": {
                        "visa": visa_identifiers,
                        "mastercard": mastercard_identifiers,
                        "amex": amex_identifiers,
                    }[payment_scheme.slug],
                }
                for payment_scheme in payment_schemes
            ],
        },
        "merchant_refs": merchant_refs,
    }


async def plan_detail_json(
    plan: Plan,
    payment_schemes: list[PaymentScheme],
    *,
    locations: int = 0,
    sub_locations: int = 0,
    mids: dict[str, int] | None = None,
    secondary_mids: dict[str, int] | None = None,
    psimis: dict[str, int] | None = None,
) -> dict:
    if mids is None:
        mids = {}
    if secondary_mids is None:
        secondary_mids = {}
    if psimis is None:
        psimis = {}
    merchants = await Merchant.objects().where(Merchant.plan == plan)
    return {
        "plan_ref": str(plan.pk),
        "plan_status": ResourceStatus(plan.status).value,
        "plan_metadata": {
            "name": plan.name,
            "plan_id": plan.plan_id,
            "slug": plan.slug,
            "icon_url": plan.icon_url,
        },
        "merchants": [
            {
                "merchant_ref": str(merchant.pk),
                "merchant_status": ResourceStatus(merchant.status).value,
                "merchant_metadata": {
                    "name": merchant.name,
                    "icon_url": merchant.icon_url,
                    "location_label": merchant.location_label,
                },
                "merchant_counts": {
                    "locations": locations,
                    "sub_locations": sub_locations,
                    "total_locations": locations + sub_locations,
                    "payment_schemes": [
                        {
                            "slug": payment_scheme.slug,
                            "mids": mids.get(payment_scheme.slug, 0),
                            "secondary_mids": secondary_mids.get(
                                payment_scheme.slug, 0
                            ),
                            "psimis": psimis.get(payment_scheme.slug, 0),
                        }
                        for payment_scheme in payment_schemes
                    ],
                },
            }
            for merchant in merchants
        ],
    }


async def test_list_no_merchants(
    plan_factory: Factory[Plan],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plans = [await plan_factory() for _ in range(3)]
    resp = test_client.get("/api/v1/plans")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [
        await plan_overview_json(plan, default_payment_schemes, merchant_refs=[])
        for plan in plans
    ]


async def test_list_with_merchants(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plans = [await plan_factory() for _ in range(3)]
    merchant_refs: dict[UUID, list[str]] = {}
    counts = {
        plan.pk: {
            "locations": 0,
            "visa": 0,
            "mastercard": 0,
            "amex": 0,
        }
        for plan in plans
    }
    for plan in plans:
        c = counts[plan.pk]
        merchant_refs[plan.pk] = []
        for _ in range(random.randint(1, 3)):
            merchant = await merchant_factory(plan=plan)
            merchant_refs[plan.pk].append(str(merchant.pk))

            # add some other resources to check the counts are working
            for _ in range(random.randint(1, 3)):
                await location_factory(merchant=merchant)
                c["locations"] += 1

            for payment_scheme in default_payment_schemes:
                for _ in range(random.randint(1, 3)):
                    await primary_mid_factory(
                        merchant=merchant, payment_scheme=payment_scheme
                    )
                    c[payment_scheme.slug] += 1

    resp = test_client.get("/api/v1/plans")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [
        await plan_overview_json(
            plan,
            default_payment_schemes,
            merchant_refs[plan.pk],
            locations=counts[plan.pk]["locations"],
            visa_identifiers=counts[plan.pk]["visa"],
            mastercard_identifiers=counts[plan.pk]["mastercard"],
            amex_identifiers=counts[plan.pk]["amex"],
        )
        for plan in plans
    ]


@pytest.mark.usefixtures("default_payment_schemes")
async def test_details(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    await merchant_factory(plan=plan)
    resp = test_client.get(f"/api/v1/plans/{plan.pk}")
    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert resp.json() == await plan_detail_json(plan, default_payment_schemes)


@pytest.mark.usefixtures("database")
async def test_details_nonexistent_plan(test_client: TestClient) -> None:
    resp = test_client.get(f"/api/v1/plans/{uuid4()}")
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_create(
    plan_factory: Factory[Plan],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
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
    assert resp.json() == await plan_overview_json(
        plan, default_payment_schemes, merchant_refs=[]
    )


async def test_create_with_blank_slug(
    plan_factory: Factory[Plan],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
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
    assert resp.json() == await plan_overview_json(
        plan, default_payment_schemes, merchant_refs=[]
    )
    assert resp.json()["plan_metadata"]["slug"] is None


async def test_create_with_duplicate_name(
    plan_factory: Factory[Plan],
    test_client: TestClient,
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


async def test_create_with_duplicate_slug(
    plan_factory: Factory[Plan],
    test_client: TestClient,
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


async def test_create_with_duplication_plan_id(
    plan_factory: Factory[Plan],
    test_client: TestClient,
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


async def test_update(
    plan_factory: Factory[Plan],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
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
    assert resp.json() == await plan_overview_json(
        plan, default_payment_schemes, merchant_refs=[]
    )
    assert plan.name == new_details.name
    assert plan.plan_id == new_details.plan_id
    assert plan.slug == new_details.slug
    assert plan.icon_url == new_details.icon_url


@pytest.mark.usefixtures("database")
async def test_update_nonexistent_plan(test_client: TestClient) -> None:
    resp = test_client.put(
        f"/api/v1/plans/{uuid4()}",
        json={
            "name": "New name",
        },
    )
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_update_with_duplicate_name(
    plan_factory: Factory[Plan],
    test_client: TestClient,
) -> None:
    plans = [await plan_factory() for _ in range(3)]
    resp = test_client.put(
        f"/api/v1/plans/{plans[0].pk}",
        json={
            "name": plans[1].name,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "name"])


async def test_update_with_duplicate_slug(
    plan_factory: Factory[Plan],
    test_client: TestClient,
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


async def test_update_with_duplicate_plan_id(
    plan_factory: Factory[Plan],
    test_client: TestClient,
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


async def test_delete_no_dependents(
    plan_factory: Factory[Plan],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    resp = test_client.delete(f"/api/v1/plans/{plan.pk}")
    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text


async def test_delete_no_onboarded_resources(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    secondary_mid_factory: Factory[SecondaryMID],
    psimi_factory: Factory[PSIMI],
    location_factory: Factory[Location],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )
    secondary_mid = await secondary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )
    psimi = await psimi_factory(merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED)
    location = await location_factory(merchant=merchant)
    secondary_mid_location_link = await secondary_mid_location_link_factory(
        secondary_mid=secondary_mid, location=location
    )

    resp = test_client.delete(f"/api/v1/plans/{plan.pk}")

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {"plan_status": "deleted"}

    expected_plan = await Plan.all_select(Plan.status).where(Plan.pk == plan.pk).first()
    assert expected_plan is not None

    expected_merchant = (
        await Merchant.all_select(Merchant.status)
        .where(Merchant.pk == merchant.pk)
        .first()
    )
    assert expected_merchant is not None

    expected_primary_mid = (
        await PrimaryMID.all_select(PrimaryMID.status)
        .where(PrimaryMID.pk == primary_mid.pk)
        .first()
    )
    assert expected_primary_mid is not None

    expected_secondary_mid = (
        await SecondaryMID.all_select(SecondaryMID.status)
        .where(SecondaryMID.pk == secondary_mid.pk)
        .first()
    )
    assert expected_secondary_mid is not None

    expected_psimi = (
        await PSIMI.all_select(PSIMI.status).where(PSIMI.pk == psimi.pk).first()
    )
    assert expected_psimi is not None

    expected_location = (
        await Location.all_select(Location.status)
        .where(Location.pk == location.pk)
        .first()
    )
    assert expected_location is not None

    assert expected_plan["status"] == ResourceStatus.DELETED
    assert expected_merchant["status"] == ResourceStatus.DELETED
    assert expected_primary_mid["status"] == ResourceStatus.DELETED
    assert expected_secondary_mid["status"] == ResourceStatus.DELETED
    assert expected_psimi["status"] == ResourceStatus.DELETED
    assert expected_location["status"] == ResourceStatus.DELETED
    assert not await SecondaryMIDLocationLink.exists().where(
        SecondaryMIDLocationLink.pk == secondary_mid_location_link.pk
    )


async def test_delete_with_onboarded_resources(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    secondary_mid_factory: Factory[SecondaryMID],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    await primary_mid_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)
    await secondary_mid_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)
    await psimi_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)

    resp = test_client.delete(f"/api/v1/plans/{plan.pk}")

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {"plan_status": "pending_deletion"}

    assert await Job.exists().where(
        Job.message_type == OffboardAndDeletePlan.__name__,
        Job.message == OffboardAndDeletePlan(plan_ref=plan.pk).dict(),
    )

    expected = await Plan.select(Plan.status).where(Plan.pk == plan.pk).first()
    assert expected is not None
    assert expected["status"] == ResourceStatus.PENDING_DELETION


@pytest.mark.usefixtures("database")
async def test_delete_nonexistent_plan(test_client: TestClient) -> None:
    resp = test_client.delete(f"/api/v1/plans/{uuid4()}")
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])
