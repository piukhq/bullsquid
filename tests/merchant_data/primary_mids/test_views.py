"""Test merchant data API endpoints that operate on primary MIDs."""
import random
from operator import itemgetter
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from ward import test

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from tests.factories import (
    merchant,
    payment_schemes,
    plan,
    primary_mid,
    primary_mid_factory,
    three_merchants,
)
from tests.fixtures import auth_header, test_client
from tests.helpers import (
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_null_error,
    assert_is_uniqueness_error,
)


async def primary_mid_to_json(primary_mid: PrimaryMID) -> dict:
    """Converts a primary MID to its expected JSON representation."""
    payment_scheme_code = (
        await PaymentScheme.select(PaymentScheme.code)
        .where(PaymentScheme.slug == primary_mid.payment_scheme)
        .first()
    )["code"]

    return {
        "mid_ref": str(primary_mid.pk),
        "mid_metadata": {
            "payment_scheme_code": payment_scheme_code,
            "mid": primary_mid.mid,
            "visa_bin": primary_mid.visa_bin,
            "payment_enrolment_status": primary_mid.payment_enrolment_status,
        },
        "date_added": primary_mid.date_added.isoformat(),
        "txm_status": primary_mid.txm_status,
    }


@test("can list primary mids")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    primary_mid: PrimaryMID = primary_mid,
) -> None:
    # work around a bug in piccolo's ModelBuilder that returns datetimes without timezones
    primary_mid = await PrimaryMID.objects().get(PrimaryMID.pk == primary_mid.pk)

    merchant_ref, plan_ref = itemgetter("merchant", "merchant.plan")(
        await PrimaryMID.select(
            PrimaryMID.merchant,
            PrimaryMID.merchant.plan,
        )
        .where(PrimaryMID.pk == primary_mid.pk)
        .first()
    )

    resp = test_client.get(
        f"/api/v1/plans/{plan_ref}/merchants/{merchant_ref}/mids", headers=auth_header
    )

    assert resp.ok, resp.json()
    assert resp.json() == {"mids": [await primary_mid_to_json(primary_mid)]}


@test("can list primary mids from a specific plan")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchants: list[Merchant] = three_merchants,
) -> None:
    for merchant in merchants:
        for _ in range(random.randint(1, 3)):
            await primary_mid_factory(merchant=merchant)

    plan_ref = (await Plan.select(Plan.pk).where(Plan.pk == merchants[0].plan).first())[
        "pk"
    ]

    resp = test_client.get(
        f"/api/v1/plans/{plan_ref}/merchants/{merchants[0].pk}/mids",
        headers=auth_header,
    )

    expected = await PrimaryMID.objects().where(PrimaryMID.merchant == merchants[0])

    assert resp.ok, resp.json()
    assert resp.json() == {
        "mids": [await primary_mid_to_json(primary_mid) for primary_mid in expected]
    }


@test("can't list primary MIDs on a plan that doesn't exist")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/mids",
        headers=auth_header,
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't list primary MIDs on a merchant that doesn't exist")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plan: Plan = plan,
) -> None:
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/mids", headers=auth_header
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can create a primary MID on a merchant")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: PaymentScheme = payment_schemes,
) -> None:
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
        headers=auth_header,
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "mid": primary_mid.mid,
                "visa_bin": primary_mid.visa_bin,
                "payment_enrolment_status": primary_mid.payment_enrolment_status,
            },
        },
    )
    assert resp.ok, resp.json()

    expected = (
        await PrimaryMID.objects()
        .where(PrimaryMID.pk == resp.json()["mid_ref"])
        .first()
    )
    assert resp.json() == await primary_mid_to_json(expected)


@test("can create a primary MID without a Visa BIN")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: PaymentScheme = payment_schemes,
) -> None:
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
        headers=auth_header,
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "mid": primary_mid.mid,
                "payment_enrolment_status": primary_mid.payment_enrolment_status,
            },
        },
    )
    assert resp.ok, resp.json()

    expected = (
        await PrimaryMID.objects()
        .where(PrimaryMID.pk == resp.json()["mid_ref"])
        .first()
    )
    assert resp.json() == await primary_mid_to_json(expected)


@test("can't create a primary MID on a plan that does not exist")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: PaymentScheme = payment_schemes,
) -> None:
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/mids",
        headers=auth_header,
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "mid": primary_mid.mid,
                "visa_bin": primary_mid.visa_bin,
                "payment_enrolment_status": primary_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't create a primary MID on a merchant that does not exist")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plan: Plan = plan,
    payment_schemes: PaymentScheme = payment_schemes,
) -> None:
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/mids",
        headers=auth_header,
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "mid": primary_mid.mid,
                "visa_bin": primary_mid.visa_bin,
                "payment_enrolment_status": primary_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't create a primary MID with a MID that already exists")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: PaymentScheme = payment_schemes,
    existing_mid: PrimaryMID = primary_mid,
) -> None:
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
        headers=auth_header,
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "mid": existing_mid.mid,
                "visa_bin": new_mid.visa_bin,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_uniqueness_error(resp, loc=["body", "mid_metadata", "mid"])


@test("can't create a primary MID with a missing payment scheme code")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
        headers=auth_header,
        json={
            "onboard": False,
            "mid_metadata": {
                "mid": new_mid.mid,
                "visa_bin": new_mid.visa_bin,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_missing_field_error(
        resp, loc=["body", "mid_metadata", "payment_scheme_code"]
    )


@test("can't create a primary MID with a null payment scheme code")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
        headers=auth_header,
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": None,
                "mid": new_mid.mid,
                "visa_bin": new_mid.visa_bin,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_null_error(resp, loc=["body", "mid_metadata", "payment_scheme_code"])


@test("can't create a primary MID with a missing MID value")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: PaymentScheme = payment_schemes,
) -> None:
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
        headers=auth_header,
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "visa_bin": new_mid.visa_bin,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_missing_field_error(resp, loc=["body", "mid_metadata", "mid"])


@test("can't create a primary MID with a null MID value")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: PaymentScheme = payment_schemes,
) -> None:
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
        headers=auth_header,
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "mid": None,
                "visa_bin": new_mid.visa_bin,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_null_error(resp, loc=["body", "mid_metadata", "mid"])


@test("can delete a single MID")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    primary_mid = await primary_mid_factory(merchant=merchant)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids/deletion",
        headers=auth_header,
        json=[str(primary_mid.pk)],
    )

    mid_status = (
        await PrimaryMID.select(PrimaryMID.status)
        .where(PrimaryMID.pk == primary_mid.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert mid_status == ResourceStatus.PENDING_DELETION
