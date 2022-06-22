"""Tests for secondary MID API endpoints."""
import random
from operator import itemgetter
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from ward import test

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from tests.fixtures import auth_header, database, test_client
from tests.helpers import (
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_null_error,
    assert_is_uniqueness_error,
)
from tests.merchant_data.factories import (
    merchant,
    merchant_factory,
    payment_schemes,
    plan,
    plan_factory,
    secondary_mid,
    secondary_mid_factory,
    three_merchants,
)


async def secondary_mid_to_json(mid: SecondaryMID) -> dict:
    """Converts a secondary MID to its expected JSON representation."""
    payment_scheme_code = (
        await PaymentScheme.select(PaymentScheme.code)
        .where(PaymentScheme.slug == mid.payment_scheme)
        .first()
    )["code"]

    return {
        "secondary_mid_ref": str(mid.pk),
        "secondary_mid_metadata": {
            "payment_scheme_code": payment_scheme_code,
            "secondary_mid": mid.secondary_mid,
            "payment_scheme_store_name": mid.payment_scheme_store_name,
            "payment_enrolment_status": mid.payment_enrolment_status,
        },
        "secondary_mid_status": mid.status,
        "date_added": mid.date_added.isoformat(),
        "txm_status": mid.txm_status,
    }


@test("can list secondary MIDs")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    secondary_mid: SecondaryMID = secondary_mid,
) -> None:
    # work around a bug in piccolo's ModelBuilder that returns datetimes without timezones
    secondary_mid = await SecondaryMID.objects().get(
        SecondaryMID.pk == secondary_mid.pk
    )

    merchant_ref, plan_ref = itemgetter("merchant", "merchant.plan")(
        await SecondaryMID.select(
            SecondaryMID.merchant,
            SecondaryMID.merchant.plan,
        )
        .where(SecondaryMID.pk == secondary_mid.pk)
        .first()
    )

    resp = test_client.get(
        f"/api/v1/plans/{plan_ref}/merchants/{merchant_ref}/secondary_mids",
        headers=auth_header,
    )

    assert resp.ok, resp.json()
    assert resp.json() == [await secondary_mid_to_json(secondary_mid)]


@test("deleted mids are not listed")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    secondary_mid: SecondaryMID = secondary_mid,
) -> None:
    # work around a bug in piccolo's ModelBuilder that returns datetimes without timezones
    secondary_mid = await SecondaryMID.objects().get(
        SecondaryMID.pk == secondary_mid.pk
    )

    merchant_ref, plan_ref = itemgetter("merchant", "merchant.plan")(
        await SecondaryMID.select(
            SecondaryMID.merchant,
            SecondaryMID.merchant.plan,
        )
        .where(SecondaryMID.pk == secondary_mid.pk)
        .first()
    )

    # create a deleted secondary MID that shouldn't be in the response
    await secondary_mid_factory(status=ResourceStatus.DELETED, merchant=merchant_ref)

    resp = test_client.get(
        f"/api/v1/plans/{plan_ref}/merchants/{merchant_ref}/secondary_mids",
        headers=auth_header,
    )

    assert resp.ok, resp.json()
    assert resp.json() == [await secondary_mid_to_json(secondary_mid)]


@test("can list secondary MIDs from a specific plan")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchants: list[Merchant] = three_merchants,
) -> None:
    for merchant in merchants:
        for _ in range(random.randint(1, 3)):
            await secondary_mid_factory(merchant=merchant)

    plan_ref = (await Plan.select(Plan.pk).where(Plan.pk == merchants[0].plan).first())[
        "pk"
    ]

    resp = test_client.get(
        f"/api/v1/plans/{plan_ref}/merchants/{merchants[0].pk}/secondary_mids",
        headers=auth_header,
    )

    expected = await SecondaryMID.objects().where(SecondaryMID.merchant == merchants[0])

    assert resp.ok, resp.json()
    assert resp.json() == [
        await secondary_mid_to_json(secondary_mid) for secondary_mid in expected
    ]


@test("can't list secondary MIDs on a plan that doesn't exist")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/secondary_mids",
        headers=auth_header,
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't list secondary MIDs on a merchant that doesn't exist")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plan: Plan = plan,
) -> None:
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/secondary_mids",
        headers=auth_header,
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can get secondary MID details")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/{secondary_mid.pk}",
        headers=auth_header,
    )

    assert resp.status_code == 200, resp.json()

    mid_ref = resp.json()["secondary_mid_ref"]
    expected = await SecondaryMID.objects().where(SecondaryMID.pk == mid_ref).first()
    assert resp.json() == await secondary_mid_to_json(expected)


@test("can't get secondary MID details from a non-existant secondary MID")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/{uuid4()}",
        headers=auth_header,
    )
    assert_is_not_found_error(resp, loc=["path", "secondary_mid_ref"])


@test("can't get secondary MID details from a non-existant merchant")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/secondary_mids/{secondary_mid.pk}",
        headers=auth_header,
    )
    assert_is_not_found_error(resp, loc=["path", "secondary_mid_ref"])


@test("can't get secondary MID details from a non-existant plan")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    merchant = await merchant_factory()
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/secondary_mids/{secondary_mid.pk}",
        headers=auth_header,
    )
    assert_is_not_found_error(resp, loc=["path", "secondary_mid_ref"])


@test("can create a secondary MID on a merchant without onboarding")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids",
        headers=auth_header,
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "secondary_mid": mid.secondary_mid,
                "payment_scheme_store_name": mid.payment_scheme_store_name,
                "payment_enrolment_status": mid.payment_enrolment_status,
            },
        },
    )
    assert resp.ok, resp.json()

    mid_ref = resp.json()["secondary_mid_ref"]
    expected = await SecondaryMID.objects().where(SecondaryMID.pk == mid_ref).first()
    assert resp.json() == await secondary_mid_to_json(expected)

    # TODO: uncomment when harmonia supports onboarding secondary MIOs.
    # assert not await Job.exists().where(
    #     Job.message_type == OnboardSecondaryMIDs.__name__,
    #     Job.message
    #     == OnboardSecondaryMIDs(secondary_mid_refs=[secondary_mid_ref]).dict(),
    # )


@test("can create and onboard a secondary MID on a merchant")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids",
        headers=auth_header,
        json={
            "onboard": True,
            "secondary_mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "secondary_mid": mid.secondary_mid,
                "payment_scheme_store_name": mid.payment_scheme_store_name,
                "payment_enrolment_status": mid.payment_enrolment_status,
            },
        },
    )
    assert resp.ok, resp.json()

    mid_ref = resp.json()["secondary_mid_ref"]

    expected = await SecondaryMID.objects().where(SecondaryMID.pk == mid_ref).first()
    assert resp.json() == await secondary_mid_to_json(expected)

    # TODO: uncomment when harmonia supports secondary MID onboarding.
    # assert await Job.exists().where(
    #     Job.message_type == OnboardSecondaryMIDs.__name__,
    #     Job.message == OnboardSecondaryMIDs(secondary_mid_refs=[secondary_mid_ref]).dict(),
    # )


@test("can create a secondary MID without a payment scheme store name")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids",
        headers=auth_header,
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "secondary_mid": mid.secondary_mid,
                "payment_enrolment_status": mid.payment_enrolment_status,
            },
        },
    )
    assert resp.ok, resp.json()

    expected = (
        await SecondaryMID.objects()
        .where(SecondaryMID.pk == resp.json()["secondary_mid_ref"])
        .first()
    )
    assert resp.json() == await secondary_mid_to_json(expected)


@test("can't create a secondary MID on a plan that does not exist")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/secondary_mids",
        headers=auth_header,
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "secondary_mid": mid.secondary_mid,
                "payment_scheme_store_name": mid.payment_scheme_store_name,
                "payment_enrolment_status": mid.payment_enrolment_status,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't create a secondary MID on a merchant that does not exist")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    plan: Plan = plan,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/secondary_mids",
        headers=auth_header,
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "secondary_mid": mid.secondary_mid,
                "payment_scheme_store_name": mid.payment_scheme_store_name,
                "payment_enrolment_status": mid.payment_enrolment_status,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't create a secondary MID with a MID that already exists")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: list[PaymentScheme] = payment_schemes,
    existing_mid: SecondaryMID = secondary_mid,
) -> None:
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids",
        headers=auth_header,
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "secondary_mid": existing_mid.secondary_mid,
                "payment_scheme_store_name": new_mid.payment_scheme_store_name,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_uniqueness_error(
        resp, loc=["body", "secondary_mid_metadata", "secondary_mid"]
    )


@test("can't create a secondary MID with a missing payment scheme code")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids",
        headers=auth_header,
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "secondary_mid": new_mid.secondary_mid,
                "payment_scheme_store_name": new_mid.payment_scheme_store_name,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_missing_field_error(
        resp, loc=["body", "secondary_mid_metadata", "payment_scheme_code"]
    )


@test("can't create a secondary MID with a null payment scheme code")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids",
        headers=auth_header,
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_code": None,
                "secondary_mid": new_mid.secondary_mid,
                "payment_scheme_store_name": new_mid.payment_scheme_store_name,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_null_error(
        resp, loc=["body", "secondary_mid_metadata", "payment_scheme_code"]
    )


@test("can't create a secondary MID with a missing MID value")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids",
        headers=auth_header,
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "payment_scheme_store_name": new_mid.payment_scheme_store_name,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_missing_field_error(
        resp, loc=["body", "secondary_mid_metadata", "secondary_mid"]
    )


@test("can't create a secondary MID with a null MID value")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
    payment_schemes: list[PaymentScheme] = payment_schemes,
) -> None:
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids",
        headers=auth_header,
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "secondary_mid": None,
                "payment_scheme_store_name": new_mid.payment_scheme_store_name,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_null_error(resp, loc=["body", "secondary_mid_metadata", "secondary_mid"])


@test("can delete a secondary MID")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    mid: SecondaryMID = secondary_mid,
) -> None:
    merchant = await mid.get_related(SecondaryMID.merchant)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids/deletion",
        headers=auth_header,
        json=[str(mid.pk)],
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {
        "secondary_mids": [
            {
                "secondary_mid_ref": str(mid.pk),
                "status": (
                    "pending_deletion"
                    if mid.txm_status == TXMStatus.ONBOARDED
                    else "deleted"
                ),
            }
        ]
    }


@test("a secondary MID that is not onboarded is deleted and no qbert job is created")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    mid = await secondary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids/deletion",
        headers=auth_header,
        json=[str(mid.pk)],
    )

    mid_status = (
        await SecondaryMID.select(SecondaryMID.status)
        .where(SecondaryMID.pk == mid.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert mid_status == ResourceStatus.DELETED

    # TODO: uncomment once harmonia supports secondary MID offboarding.
    # assert not await Job.exists().where(
    #     Job.message_type == OffboardAndDeleteSecondaryMIDs.__name__,
    #     Job.message == OffboardAndDeleteSecondaryMIDs(secondary_mid_refs=[secondary_mid.pk]).dict(),
    # )


@test("a secondary MID that is offboarded is deleted and no qbert job is created")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    mid = await secondary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.OFFBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids/deletion",
        headers=auth_header,
        json=[str(mid.pk)],
    )

    mid_status = (
        await SecondaryMID.select(SecondaryMID.status)
        .where(SecondaryMID.pk == mid.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert mid_status == ResourceStatus.DELETED

    # TODO: uncomment once harmonia supports secondary MID offboarding.
    # assert not await Job.exists().where(
    #     Job.message_type == OffboardAndDeleteSecondaryMIDs.__name__,
    #     Job.message == OffboardAndDeleteSecondaryMIDs(secondary_mid_refs=[secondary_mid.pk]).dict(),
    # )


@test(
    "a secondary MID that is onboarded goes to pending deletion and a qbert job is created"
)
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    mid = await secondary_mid_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids/deletion",
        headers=auth_header,
        json=[str(mid.pk)],
    )

    mid_status = (
        await SecondaryMID.select(SecondaryMID.status)
        .where(SecondaryMID.pk == mid.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert mid_status == ResourceStatus.PENDING_DELETION

    # TODO: uncomment once harmonia supports secondary MID onboarding.
    # assert await Job.exists().where(
    #     Job.message_type == OffboardAndDeleteSecondaryMIDs.__name__,
    #     Job.message == OffboardAndDeleteSecondaryMIDs(secondary_mid_refs=[secondary_mid.pk]).dict(),
    # )


@test("deleting a secondary MID that doesn't exist returns a useful error")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids/deletion",
        headers=auth_header,
        json=[str(uuid4())],
    )

    assert_is_not_found_error(resp, loc=["body", "secondary_mid_refs"])


@test("sending a delete secondary MIDs request with an empty body does nothing")
def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids/deletion",
        headers=auth_header,
        json=[],
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {"secondary_mids": []}
