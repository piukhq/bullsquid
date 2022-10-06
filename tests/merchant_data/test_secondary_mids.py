"""Tests for secondary MID API endpoints."""
import random
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from ward import test

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from tests.fixtures import database, test_client
from tests.helpers import (
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_null_error,
    assert_is_uniqueness_error,
)
from tests.merchant_data.factories import (
    default_payment_schemes,
    location_factory,
    merchant_factory,
    plan_factory,
    secondary_mid_factory,
    secondary_mid_location_link_factory,
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids"
    )

    assert resp.status_code == status.HTTP_200_OK

    secondary_mid = await SecondaryMID.objects().get(
        SecondaryMID.pk == secondary_mid.pk
    )
    assert resp.json() == [await secondary_mid_to_json(secondary_mid)]


@test("deleted mids are not listed")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    # create a deleted secondary MID that shouldn't be in the response
    await secondary_mid_factory(status=ResourceStatus.DELETED, merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids"
    )

    assert resp.status_code == status.HTTP_200_OK

    secondary_mid = await SecondaryMID.objects().get(
        SecondaryMID.pk == secondary_mid.pk
    )
    assert resp.json() == [await secondary_mid_to_json(secondary_mid)]


@test("can list secondary MIDs from a specific plan")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchants = [await merchant_factory(plan=plan) for _ in range(3)]
    for merchant in merchants:
        for _ in range(random.randint(1, 3)):
            await secondary_mid_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchants[0].pk}/secondary_mids"
    )

    expected = await SecondaryMID.objects().where(SecondaryMID.merchant == merchants[0])

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [
        await secondary_mid_to_json(secondary_mid) for secondary_mid in expected
    ]


@test("can't list secondary MIDs on a plan that doesn't exist")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/secondary_mids"
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can't list secondary MIDs on a merchant that doesn't exist")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/secondary_mids"
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can list secondary MIDs excluding a location")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    payment_schemes = await default_payment_schemes()
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mids = [
        await secondary_mid_factory(merchant=merchant),
        await secondary_mid_factory(merchant=merchant),
        await secondary_mid_factory(merchant=merchant),
        await secondary_mid_factory(merchant=merchant),
        await secondary_mid_factory(merchant=merchant),
    ]

    # associate the first three locations with the secondary mid
    for secondary_mid in secondary_mids[:3]:
        await secondary_mid_location_link_factory(
            location=location, secondary_mid=secondary_mid
        )

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        params={"exclude_location": str(location.pk)},
    )

    assert resp.status_code == 200

    expected = await SecondaryMID.objects().where(
        SecondaryMID.pk.is_in(
            [secondary_mid.pk for secondary_mid in secondary_mids[-2:]]
        )
    )
    assert resp.json() == [
        await secondary_mid_to_json(secondary_mid) for secondary_mid in expected
    ]


@test("can list secondary mids excluding a location that isn't linked to anything")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        params={"exclude_location": str(location.pk)},
    )

    assert resp.status_code == 200

    secondary_mid = await SecondaryMID.objects().get(
        SecondaryMID.pk == secondary_mid.pk
    )
    assert resp.json() == [await secondary_mid_to_json(secondary_mid)]


@test("can't exclude a location that doesn't exist")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        params={"exclude_location": str(uuid4())},
    )

    assert_is_not_found_error(resp, loc=["query", "exclude_location"])


@test("can't exclude a location from a different merchant")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory()

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        params={"exclude_location": str(location.pk)},
    )

    assert_is_not_found_error(resp, loc=["query", "exclude_location"])


@test("can get secondary MID details")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/{secondary_mid.pk}"
    )

    assert resp.status_code == status.HTTP_200_OK, resp.json()

    mid_ref = resp.json()["secondary_mid_ref"]
    expected = await SecondaryMID.objects().where(SecondaryMID.pk == mid_ref).first()
    assert resp.json() == await secondary_mid_to_json(expected)


@test("can't get secondary MID details from a non-existent secondary MID")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/{uuid4()}"
    )
    assert_is_not_found_error(resp, loc=["path", "secondary_mid_ref"])


@test("can't get secondary MID details from a non-existent merchant")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/secondary_mids/{secondary_mid.pk}"
    )
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't get secondary MID details from a non-existent plan")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/secondary_mids/{secondary_mid.pk}"
    )
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can create a secondary MID on a merchant without onboarding")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    payment_schemes = await default_payment_schemes()
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
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
    assert resp.status_code == status.HTTP_201_CREATED

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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory(plan=plan)
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
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
    assert resp.status_code == status.HTTP_201_CREATED

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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory(plan=plan)
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "secondary_mid": mid.secondary_mid,
                "payment_enrolment_status": mid.payment_enrolment_status,
            },
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED

    expected = (
        await SecondaryMID.objects()
        .where(SecondaryMID.pk == resp.json()["secondary_mid_ref"])
        .first()
    )
    assert resp.json() == await secondary_mid_to_json(expected)


@test("can't create a secondary MID on a plan that does not exist")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory()
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/secondary_mids",
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

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can't create a secondary MID on a merchant that does not exist")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    plan = await plan_factory()
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/secondary_mids",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    existing_mid = await secondary_mid_factory()
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory(plan=plan)
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
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


@test("can't create a secondary MID with an invalid payment scheme code")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_code": 9,
                "secondary_mid": new_mid.secondary_mid,
                "payment_scheme_store_name": new_mid.payment_scheme_store_name,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_not_found_error(
        resp, loc=["body", "secondary_mid_metadata", "payment_scheme_code"]
    )


@test("can't create a secondary MID with a missing MID value")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    payment_schemes = await default_payment_schemes()
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    payment_schemes = await default_payment_schemes()
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await secondary_mid_factory(merchant=merchant)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/deletion",
        json={"secondary_mid_refs": [str(mid.pk)]},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == [
        {
            "secondary_mid_ref": str(mid.pk),
            "status": (
                "pending_deletion"
                if mid.txm_status == TXMStatus.ONBOARDED
                else "deleted"
            ),
        }
    ]


@test("deleting a secondary MID that is linked to a location also deletes the link")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    await secondary_mid_location_link_factory(secondary_mid=secondary_mid)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/deletion",
        json={"secondary_mid_refs": [str(secondary_mid.pk)]},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert not await SecondaryMIDLocationLink.exists().where(
        SecondaryMIDLocationLink.secondary_mid == secondary_mid
    )


@test("a secondary MID that is not onboarded is deleted and no qbert job is created")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await secondary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/deletion",
        json={"secondary_mid_refs": [str(mid.pk)]},
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await secondary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.OFFBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/deletion",
        json={"secondary_mid_refs": [str(mid.pk)]},
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await secondary_mid_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/deletion",
        json={"secondary_mid_refs": [str(mid.pk)]},
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/deletion",
        json={"secondary_mid_refs": [str(uuid4())]},
    )

    assert_is_not_found_error(resp, loc=["body", "secondary_mid_refs"])


@test("sending a delete secondary MIDs request with an empty body does nothing")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/deletion",
        json={"secondary_mid_refs": []},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == []


@test("can associate a location with a secondary mid")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    location = await location_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/{secondary_mid.pk}/secondary_mid_location_links",
        json={"location_refs": [str(location.pk)]},
    )

    assert resp.status_code == status.HTTP_201_CREATED

    link = (
        await SecondaryMIDLocationLink.select(SecondaryMIDLocationLink.pk)
        .where(
            SecondaryMIDLocationLink.secondary_mid == secondary_mid,
            SecondaryMIDLocationLink.location == location,
        )
        .first()
    )
    assert resp.json() == [
        {
            "link_ref": str(link["pk"]),
            "location_ref": str(location.pk),
            "location_title": location.title,
        }
    ]


@test("can't associate a location with a secondary mid on a different merchant")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    location = await location_factory()

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/{secondary_mid.pk}/secondary_mid_location_links",
        json={"location_refs": [str(location.pk)]},
    )

    assert_is_not_found_error(resp, loc=["body", "location_ref"])


@test("can't associate a location with a secondary mid that doesn't exist")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/{uuid4()}/secondary_mid_location_links",
        json={"location_refs": [str(location.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "secondary_mid_ref"])


@test("can't associate a location with a secondary mid on a non-existent merchant")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    location = await location_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/secondary_mids/{secondary_mid.pk}/secondary_mid_location_links",
        json={"location_refs": [str(location.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't associate a location with a secondary mid on a non-existent plan")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    merchant = await merchant_factory()
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    location = await location_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/secondary_mids/{secondary_mid.pk}/secondary_mid_location_links",
        json={"location_refs": [str(location.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test(
    "creating the same location association twice only creates a single database record"
)
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    """
    We don't actually need to check the database in this test - the unique
    constraint will prevent the insertion of a second association.
    """
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    location = await location_factory(merchant=merchant)

    url = f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/{secondary_mid.pk}/secondary_mid_location_links"
    json = {"location_refs": [str(location.pk)]}

    resp1 = test_client.post(url, json=json)
    assert resp1.status_code == status.HTTP_201_CREATED

    resp2 = test_client.post(url, json=json)
    assert resp2.status_code == status.HTTP_200_OK

    assert resp1.json()[0]["link_ref"] == resp2.json()[0]["link_ref"]


@test("can list locations associated with a secondary mid")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    link = await secondary_mid_location_link_factory(
        location=location, secondary_mid=secondary_mid
    )

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/{secondary_mid.pk}/secondary_mid_location_links"
    )

    assert resp.status_code == status.HTTP_200_OK

    assert resp.json() == [
        {
            "link_ref": str(link.pk),
            "location_ref": str(location.pk),
            "location_title": location.title,
        }
    ]


@test("can't list locations associated with a secondary mid that doesn't exist")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    await secondary_mid_location_link_factory(
        location=location, secondary_mid=secondary_mid
    )

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/{uuid4()}/secondary_mid_location_links"
    )

    assert_is_not_found_error(resp, loc=["path", "secondary_mid_ref"])


@test(
    "can't list locations associated with a secondary mid on a merchant that doesn't exist"
)
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    await secondary_mid_location_link_factory(
        location=location, secondary_mid=secondary_mid
    )

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/secondary_mids/{secondary_mid.pk}/secondary_mid_location_links"
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test(
    "can't list secondary mids associated with a location on a plan that doesn't exist"
)
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    await secondary_mid_location_link_factory(
        location=location, secondary_mid=secondary_mid
    )

    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/secondary_mids/{secondary_mid.pk}/secondary_mid_location_links"
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])
