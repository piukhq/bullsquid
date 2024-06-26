"""Test merchant data API endpoints that operate on merchants."""

import itertools
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from qbert.tables import Job

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.db import get_merchant
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.psimis.tables import PSIMI
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from bullsquid.merchant_data.tasks import OffboardAndDeleteMerchant, run_worker
from tests.helpers import (
    Factory,
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_uniqueness_error,
    assert_is_value_error,
)


def merchant_overview_json(
    merchant: Merchant,
    payment_schemes: list[PaymentScheme],
    *,
    locations: int = 0,
    sub_locations: int = 0,
    mids: dict[str, int] | None = None,
    secondary_mids: dict[str, int] | None = None,
    psimis: dict[str, int] | None = None,
) -> dict:
    """Convert a merchant to its expected list JSON representation."""
    if mids is None:
        mids = {}
    if secondary_mids is None:
        secondary_mids = {}
    if psimis is None:
        psimis = {}

    return {
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
                    "secondary_mids": secondary_mids.get(payment_scheme.slug, 0),
                    "psimis": psimis.get(payment_scheme.slug, 0),
                }
                for payment_scheme in payment_schemes
            ],
        },
    }


def merchant_detail_json(
    merchant: Merchant,
    plan: Plan,
    payment_schemes: list[PaymentScheme],
    *,
    locations: int = 0,
    sub_locations: int = 0,
    mids: dict[str, int] | None = None,
    secondary_mids: dict[str, int] | None = None,
    psimis: dict[str, int] | None = None,
) -> dict:
    """Convert a merchant to its expected detail JSON representation."""
    if mids is None:
        mids = {}
    if secondary_mids is None:
        secondary_mids = {}
    if psimis is None:
        psimis = {}

    return {
        "merchant_ref": str(merchant.pk),
        "merchant_status": ResourceStatus(merchant.status).value,
        "merchant_counts": {
            "locations": locations,
            "sub_locations": sub_locations,
            "total_locations": locations + sub_locations,
            "payment_schemes": [
                {
                    "slug": payment_scheme.slug,
                    "mids": mids.get(payment_scheme.slug, 0),
                    "secondary_mids": secondary_mids.get(payment_scheme.slug, 0),
                    "psimis": psimis.get(payment_scheme.slug, 0),
                }
                for payment_scheme in payment_schemes
            ],
        },
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


async def test_list(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchants = [
        await merchant_factory(plan=plan),
        await merchant_factory(plan=plan),
        await merchant_factory(plan=plan),
    ]

    for merchant, _ in itertools.product(merchants, range(3)):
        await location_factory(merchant=merchant)
        await primary_mid_factory(
            merchant=merchant, payment_scheme=default_payment_schemes[0]
        )

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [
        merchant_overview_json(
            merchant,
            default_payment_schemes,
            locations=3,
            mids={"visa": 3},
        )
        for merchant in merchants
    ]


@pytest.mark.usefixtures("database")
async def test_list_nonexistent_plan(test_client: TestClient) -> None:
    resp = test_client.get(f"/api/v1/plans/{uuid4()}/merchants")
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_details(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == merchant_detail_json(
        merchant, plan, payment_schemes=default_payment_schemes
    )


async def test_details_with_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.get(f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}")
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_details_with_nonexistent_merchant(
    plan_factory: Factory[Plan],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}")
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_create(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
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
    assert resp.json() == merchant_overview_json(merchant, default_payment_schemes)


async def test_create_with_duplicate_name(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    existing_merchant = await merchant_factory(plan=plan)
    new_merchant = await merchant_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants",
        json={
            "name": existing_merchant.name,
            "icon_url": new_merchant.icon_url,
            "location_label": new_merchant.location_label,
        },
    )
    assert_is_uniqueness_error(resp, loc=["body", "name"])


async def test_create_with_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
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


async def test_create_with_blank_name(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
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


async def test_create_with_blank_location_label(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
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


async def test_update(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    new_details = await merchant_factory(persist=False)
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}",
        json={
            "name": new_details.name,
            "icon_url": new_details.icon_url,
            "location_label": new_details.location_label,
        },
    )
    assert resp.status_code == status.HTTP_200_OK

    expected = await Merchant.objects().get(Merchant.pk == merchant.pk)
    assert expected is not None

    assert resp.json() == merchant_overview_json(
        expected, await PaymentScheme.objects()
    )
    assert expected.name == new_details.name
    assert expected.icon_url == new_details.icon_url
    assert expected.location_label == new_details.location_label


async def test_update_without_name(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}",
        json={"location_label": "new location"},
    )
    assert_is_missing_field_error(resp, loc=["body", "name"])


async def test_update_without_location_label(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}",
        json={"name": "new name"},
    )
    assert_is_missing_field_error(resp, loc=["body", "location_label"])


async def test_update_nonexistent_merchant(
    plan_factory: Factory[Plan],
    test_client: TestClient,
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


async def test_update_with_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
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


async def test_update_with_duplicate_name(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
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


async def test_list_deleted_merchants(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)

    # create a deleted merchant that shouldn't be in the response
    await merchant_factory(status=ResourceStatus.DELETED)

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants")

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [merchant_overview_json(merchant, default_payment_schemes)]


async def test_delete_with_no_onboarded_resources(
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

    resp = test_client.delete(f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}")

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {"merchant_status": "deleted"}

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

    resp = test_client.delete(f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}")

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {"merchant_status": "pending_deletion"}

    assert await Job.exists().where(
        Job.message_type == OffboardAndDeleteMerchant.__name__,
        Job.message == OffboardAndDeleteMerchant(merchant_ref=merchant.pk).dict(),
    )

    expected = (
        await Merchant.select(Merchant.status).where(Merchant.pk == merchant.pk).first()
    )
    assert expected is not None
    assert expected["status"] == ResourceStatus.PENDING_DELETION

    # 4 tasks: delete primary mid, delete secondary mid, delete psimi, delete merchant
    for _ in range(4):
        await run_worker(burst=True)


async def test_delete_noexistent_merchant(
    plan_factory: Factory[Plan],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    resp = test_client.delete(f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}")
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_delete_with_noexistent_plan(
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.delete(f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}")
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_plan_validation() -> None:
    with pytest.raises(ValueError) as ex:
        await get_merchant(uuid4(), plan_ref=None)
    assert ex.value.args[0] == "validate_plan cannot be true if plan_ref is null"
