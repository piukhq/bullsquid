"""Test merchant data API endpoints that operate on primary MIDs."""
import random
from operator import itemgetter
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from qbert.tables import Job
from ward import test

from bullsquid.merchant_data.enums import (
    PaymentEnrolmentStatus,
    ResourceStatus,
    TXMStatus,
)
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.tasks import OffboardAndDeletePrimaryMIDs, OnboardPrimaryMIDs
from tests.fixtures import database, test_client
from tests.helpers import (
    assert_is_data_error,
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_null_error,
    assert_is_uniqueness_error,
)
from tests.merchant_data.factories import (
    default_payment_schemes,
    merchant_factory,
    plan_factory,
    primary_mid_factory,
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
        "mid_status": primary_mid.status,
        "date_added": primary_mid.date_added.isoformat(),
        "txm_status": primary_mid.txm_status,
    }


@test("can list primary mids")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(merchant=merchant)

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids")

    assert resp.status_code == status.HTTP_200_OK

    primary_mid = await PrimaryMID.objects().get(PrimaryMID.pk == primary_mid.pk)
    assert resp.json() == [await primary_mid_to_json(primary_mid)]


@test("deleted mids are not listed")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(merchant=merchant)

    # create a deleted primary MID that shouldn't be in the response
    await primary_mid_factory(status=ResourceStatus.DELETED, merchant=merchant.pk)

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids")

    assert resp.status_code == status.HTTP_200_OK

    primary_mid = await PrimaryMID.objects().get(PrimaryMID.pk == primary_mid.pk)
    assert resp.json() == [await primary_mid_to_json(primary_mid)]


@test("can list primary mids from a specific plan")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchants = [await merchant_factory() for _ in range(3)]
    for merchant in merchants:
        for _ in range(random.randint(1, 3)):
            await primary_mid_factory(merchant=merchant)

    plan_ref = (await Plan.select(Plan.pk).where(Plan.pk == merchants[0].plan).first())[
        "pk"
    ]

    resp = test_client.get(f"/api/v1/plans/{plan_ref}/merchants/{merchants[0].pk}/mids")

    expected = await PrimaryMID.objects().where(PrimaryMID.merchant == merchants[0])

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [
        await primary_mid_to_json(primary_mid) for primary_mid in expected
    ]


@test("can't list primary MIDs on a plan that doesn't exist")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.get(f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/mids")

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can't list primary MIDs on a merchant that doesn't exist")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/mids")

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can create a primary MID on a merchant without onboarding")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    payment_schemes = await default_payment_schemes()
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
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
    assert resp.status_code == status.HTTP_201_CREATED

    mid_ref = resp.json()["mid_ref"]

    expected = await PrimaryMID.objects().where(PrimaryMID.pk == mid_ref).first()
    assert resp.json() == await primary_mid_to_json(expected)

    assert not await Job.exists().where(
        Job.message_type == OnboardPrimaryMIDs.__name__,
        Job.message == OnboardPrimaryMIDs(mid_refs=[mid_ref]).dict(),
    )


@test("can create and onboard a primary MID on a merchant")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    payment_schemes = await default_payment_schemes()
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
        json={
            "onboard": True,
            "mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "mid": primary_mid.mid,
                "visa_bin": primary_mid.visa_bin,
                "payment_enrolment_status": primary_mid.payment_enrolment_status,
            },
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED

    mid_ref = resp.json()["mid_ref"]

    expected = await PrimaryMID.objects().where(PrimaryMID.pk == mid_ref).first()
    assert resp.json() == await primary_mid_to_json(expected)

    assert await Job.exists().where(
        Job.message_type == OnboardPrimaryMIDs.__name__,
        Job.message == OnboardPrimaryMIDs(mid_refs=[mid_ref]).dict(),
    )


@test("can create a primary MID without a Visa BIN")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory()
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "mid": primary_mid.mid,
                "payment_enrolment_status": primary_mid.payment_enrolment_status,
            },
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED

    expected = (
        await PrimaryMID.objects()
        .where(PrimaryMID.pk == resp.json()["mid_ref"])
        .first()
    )
    assert resp.json() == await primary_mid_to_json(expected)


@test("can't create a primary MID on a plan that does not exist")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory()
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/mids",
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

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can't create a primary MID on a merchant that does not exist")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    plan = await plan_factory()
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/mids",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    existing_mid = await primary_mid_factory()
    merchant = await merchant_factory()
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory()
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory()
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids",
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


@test("a primary MID can have its enrolment status updated")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await primary_mid_factory(
        merchant=merchant, payment_enrolment_status=PaymentEnrolmentStatus.UNKNOWN
    )
    mid = await PrimaryMID.objects().get(PrimaryMID.pk == mid.pk)

    resp = test_client.patch(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/{mid.pk}",
        json={"payment_enrolment_status": PaymentEnrolmentStatus.ENROLLED},
    )

    assert resp.status_code == status.HTTP_200_OK, resp.json()

    expected = await primary_mid_to_json(mid)
    expected["mid_metadata"][
        "payment_enrolment_status"
    ] = PaymentEnrolmentStatus.ENROLLED.value
    assert resp.json() == expected


@test("a visa primary MID can have its visa BIN updated")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await primary_mid_factory(
        merchant=merchant,
        payment_scheme=payment_schemes[0],
    )
    mid = await PrimaryMID.objects().get(PrimaryMID.pk == mid.pk)

    resp = test_client.patch(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/{mid.pk}",
        json={"visa_bin": "new-test-visa-bin"},
    )

    assert resp.status_code == status.HTTP_200_OK, resp.text

    expected = await primary_mid_to_json(mid)
    expected["mid_metadata"]["visa_bin"] = "new-test-visa-bin"
    assert resp.json() == expected


@test("a non-visa primary MID cannot have its visa BIN updated")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await primary_mid_factory(
        merchant=merchant,
        payment_scheme=payment_schemes[1],
    )
    original_visa_bin = mid.visa_bin

    resp = test_client.patch(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/{mid.pk}",
        json={"visa_bin": "new-test-visa-bin"},
    )
    assert_is_data_error(resp, loc=["body", "visa_bin"])

    mid = await PrimaryMID.objects().get(PrimaryMID.pk == mid.pk)
    assert mid.visa_bin == original_visa_bin


@test("attempting to update a non-existent primary MID raises an error")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.patch(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/{uuid4()}",
        json={"payment_enrolment_status": PaymentEnrolmentStatus.ENROLLING},
    )

    assert_is_not_found_error(resp, loc=["path", "mid_ref"])


@test("attempting to update a primary MID on a non-existent merchant raises an error")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await primary_mid_factory(merchant=merchant)
    resp = test_client.patch(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/mids/{mid.pk}",
        json={"payment_enrolment_status": PaymentEnrolmentStatus.ENROLLING},
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("attempting to update a primary MID on a non-existent plan raises an error")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    mid = await primary_mid_factory(merchant=merchant)
    resp = test_client.patch(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/mids/{mid.pk}",
        json={"payment_enrolment_status": PaymentEnrolmentStatus.ENROLLING},
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("a MID that is not onboarded is deleted and no qbert job is created")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    primary_mid = await primary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids/deletion",
        json={"mid_refs": [str(primary_mid.pk)]},
    )

    mid_status = (
        await PrimaryMID.select(PrimaryMID.status)
        .where(PrimaryMID.pk == primary_mid.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert mid_status == ResourceStatus.DELETED

    assert not await Job.exists().where(
        Job.message_type == OffboardAndDeletePrimaryMIDs.__name__,
        Job.message == OffboardAndDeletePrimaryMIDs(mid_refs=[primary_mid.pk]).dict(),
    )


@test("a MID that is offboarded is deleted and no qbert job is created")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    primary_mid = await primary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.OFFBOARDED
    )
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids/deletion",
        json={"mid_refs": [str(primary_mid.pk)]},
    )

    mid_status = (
        await PrimaryMID.select(PrimaryMID.status)
        .where(PrimaryMID.pk == primary_mid.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert mid_status == ResourceStatus.DELETED

    assert not await Job.exists().where(
        Job.message_type == OffboardAndDeletePrimaryMIDs.__name__,
        Job.message == OffboardAndDeletePrimaryMIDs(mid_refs=[primary_mid.pk]).dict(),
    )


@test("a MID that is onboarded goes to pending deletion and a qbert job is created")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    primary_mid = await primary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.ONBOARDED
    )
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids/deletion",
        json={"mid_refs": [str(primary_mid.pk)]},
    )

    mid_status = (
        await PrimaryMID.select(PrimaryMID.status)
        .where(PrimaryMID.pk == primary_mid.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert mid_status == ResourceStatus.PENDING_DELETION

    assert await Job.exists().where(
        Job.message_type == OffboardAndDeletePrimaryMIDs.__name__,
        Job.message == OffboardAndDeletePrimaryMIDs(mid_refs=[primary_mid.pk]).dict(),
    )


@test("deleting a MID that doesn't exist gives a useful error")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids/deletion",
        json={"mid_refs": [str(uuid4())]},
    )

    assert_is_not_found_error(resp, loc=["body", "mid_refs"])


@test("sending a delete MIDs request with an empty body does nothing")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/mids/deletion",
        json={"mid_refs": []},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == []
