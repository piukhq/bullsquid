"""Test merchant data API endpoints that operate on primary MIDs."""
import random
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from qbert.tables import Job

from bullsquid.merchant_data.enums import (
    PaymentEnrolmentStatus,
    ResourceStatus,
    TXMStatus,
)
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.tasks import (
    OffboardAndDeletePrimaryMIDs,
    OnboardPrimaryMIDs,
)
from tests.helpers import (
    Factory,
    assert_is_data_error,
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
        "mid_status": primary_mid.status,
        "date_added": primary_mid.date_added.isoformat(),
        "txm_status": primary_mid.txm_status,
    }


async def test_list(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(merchant=merchant)

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids")

    assert resp.status_code == status.HTTP_200_OK

    primary_mid = await PrimaryMID.objects().get(PrimaryMID.pk == primary_mid.pk)
    assert resp.json() == [await primary_mid_to_json(primary_mid)]


async def test_list_deleted_mids(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
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


async def test_list_by_plan(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchants = [await merchant_factory(plan=plan) for _ in range(3)]
    for merchant in merchants:
        for _ in range(random.randint(1, 3)):
            await primary_mid_factory(merchant=merchant)

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{merchants[0].pk}/mids")

    expected = await PrimaryMID.objects().where(PrimaryMID.merchant == merchants[0])

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [
        await primary_mid_to_json(primary_mid) for primary_mid in expected
    ]


async def test_list_with_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.get(f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/mids")

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_list_with_nonexistent_merchant(
    plan_factory: Factory[Plan],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/mids")

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_create_without_onboarding(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids",
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": default_payment_schemes[0].code,
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


async def test_create_non_visa_mid_with_visa_bin(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(
        persist=False, payment_scheme=default_payment_schemes[2], visa_bin="test"
    )
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids",
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": default_payment_schemes[2].code,
                "mid": primary_mid.mid,
                "visa_bin": primary_mid.visa_bin,
                "payment_enrolment_status": primary_mid.payment_enrolment_status,
            },
        },
    )
    assert_is_data_error(resp, loc=["body", "mid_metadata", "visa_bin"])


async def test_create_and_onboard(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids",
        json={
            "onboard": True,
            "mid_metadata": {
                "payment_scheme_code": default_payment_schemes[0].code,
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


async def test_create_without_visa_bin(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids",
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": default_payment_schemes[0].code,
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


async def test_create_with_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/mids",
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": default_payment_schemes[0].code,
                "mid": primary_mid.mid,
                "visa_bin": primary_mid.visa_bin,
                "payment_enrolment_status": primary_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_create_with_nonexistent_merchant(
    plan_factory: Factory[Plan],
    primary_mid_factory: Factory[PrimaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    primary_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/mids",
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": default_payment_schemes[0].code,
                "mid": primary_mid.mid,
                "visa_bin": primary_mid.visa_bin,
                "payment_enrolment_status": primary_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_create_with_duplicate_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    existing_mid = await primary_mid_factory()
    merchant = await merchant_factory(plan=plan)
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids",
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": default_payment_schemes[0].code,
                "mid": existing_mid.mid,
                "visa_bin": new_mid.visa_bin,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_uniqueness_error(resp, loc=["body", "mid_metadata", "mid"])


async def test_create_without_payment_scheme_code(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids",
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


async def test_create_with_null_payment_scheme_code(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids",
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


async def test_create_without_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids",
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": default_payment_schemes[0].code,
                "visa_bin": new_mid.visa_bin,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_missing_field_error(resp, loc=["body", "mid_metadata", "mid"])


async def test_create_with_null_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    new_mid = await primary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids",
        json={
            "onboard": False,
            "mid_metadata": {
                "payment_scheme_code": default_payment_schemes[0].code,
                "mid": None,
                "visa_bin": new_mid.visa_bin,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_null_error(resp, loc=["body", "mid_metadata", "mid"])


async def test_update_enrolment_status(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
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


async def test_update_visa_bin(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await primary_mid_factory(
        merchant=merchant,
        payment_scheme=default_payment_schemes[0],
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


async def test_update_visa_bin_on_non_visa_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await primary_mid_factory(
        merchant=merchant,
        payment_scheme=default_payment_schemes[1],
    )
    original_visa_bin = mid.visa_bin

    resp = test_client.patch(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/{mid.pk}",
        json={"visa_bin": "new-test-visa-bin"},
    )
    assert_is_data_error(resp, loc=["body", "visa_bin"])

    mid = await PrimaryMID.objects().get(PrimaryMID.pk == mid.pk)
    assert mid.visa_bin == original_visa_bin


async def test_update_notexistent_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.patch(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/{uuid4()}",
        json={"payment_enrolment_status": PaymentEnrolmentStatus.ENROLLING},
    )

    assert_is_not_found_error(resp, loc=["path", "mid_ref"])


async def test_update_with_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await primary_mid_factory(merchant=merchant)
    resp = test_client.patch(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/mids/{mid.pk}",
        json={"payment_enrolment_status": PaymentEnrolmentStatus.ENROLLING},
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_update_with_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    mid = await primary_mid_factory(merchant=merchant)
    resp = test_client.patch(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/mids/{mid.pk}",
        json={"payment_enrolment_status": PaymentEnrolmentStatus.ENROLLING},
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_delete_not_onboarded(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/deletion",
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


async def test_delete_offboarded(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.OFFBOARDED
    )
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/deletion",
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


async def test_delete_onboarded(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.ONBOARDED
    )
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/deletion",
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


async def test_delete_with_linked_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory(
        merchant=merchant, location=location, txm_status=TXMStatus.NOT_ONBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/deletion",
        json={"mid_refs": [str(primary_mid.pk)]},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED

    primary_mid = await PrimaryMID.objects().get(PrimaryMID.pk == primary_mid.pk)
    assert primary_mid.location is None


async def test_delete_nonexistent_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/deletion",
        json={"mid_refs": [str(uuid4())]},
    )

    assert_is_not_found_error(resp, loc=["body", "mid_refs"])


async def test_delete_zero_mids(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/deletion",
        json={"mid_refs": []},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == []


async def test_associate_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(merchant=merchant)
    location = await location_factory(merchant=merchant)

    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/{primary_mid.pk}/location_link",
        json={"location_ref": str(location.pk)},
    )

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        "location_ref": str(location.pk),
        "location_title": location.title,
    }


async def test_associate_location_wrong_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(merchant=merchant)
    location = await location_factory()

    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/{primary_mid.pk}/location_link",
        json={"location_ref": str(location.pk)},
    )

    assert_is_not_found_error(resp, loc=["body", "location_ref"])


async def test_associate_location_nonexistent_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)

    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/{uuid4()}/location_link",
        json={"location_ref": str(location.pk)},
    )

    assert_is_not_found_error(resp, loc=["path", "mid_ref"])


async def test_associate_location_with_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(merchant=merchant)
    location = await location_factory(merchant=merchant)

    resp = test_client.put(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/mids/{primary_mid.pk}/location_link",
        json={"location_ref": str(location.pk)},
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_associate_location_with_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    primary_mid = await primary_mid_factory(merchant=merchant)
    location = await location_factory(merchant=merchant)

    resp = test_client.put(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/mids/{primary_mid.pk}/location_link",
        json={"location_ref": str(location.pk)},
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_delete_location_link(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    mid = await primary_mid_factory(merchant=merchant, location=location)

    resp = test_client.delete(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/{mid.pk}/location_link"
    )

    assert resp.status_code == status.HTTP_204_NO_CONTENT

    mid = await PrimaryMID.objects().get(PrimaryMID.pk == mid.pk)
    assert mid.location is None


async def test_delete_location_link_unlinked_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await primary_mid_factory(merchant=merchant)

    resp = test_client.delete(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/{mid.pk}/location_link"
    )

    assert resp.status_code == status.HTTP_204_NO_CONTENT


async def test_delete_location_link_nonexistent_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)

    resp = test_client.delete(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/mids/{uuid4()}/location_link"
    )

    assert_is_not_found_error(resp, loc=["path", "mid_ref"])


async def test_delete_location_link_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    mid = await primary_mid_factory(merchant=merchant, location=location)

    resp = test_client.delete(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/mids/{mid.pk}/location_link"
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_delete_location_link_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)
    mid = await primary_mid_factory(merchant=merchant, location=location)

    resp = test_client.delete(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/mids/{mid.pk}/location_link"
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])
