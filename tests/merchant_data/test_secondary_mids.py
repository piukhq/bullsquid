"""Tests for secondary MID API endpoints."""
import random
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from tests.helpers import (
    Factory,
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_null_error,
    assert_is_uniqueness_error,
)


async def secondary_mid_to_json(mid: SecondaryMID) -> dict:
    """Converts a secondary MID to its expected JSON representation."""
    return {
        "secondary_mid_ref": str(mid.pk),
        "secondary_mid_metadata": {
            "payment_scheme_slug": mid.payment_scheme,
            "secondary_mid": mid.secondary_mid,
            "payment_scheme_store_name": mid.payment_scheme_store_name,
            "payment_enrolment_status": mid.payment_enrolment_status,
        },
        "secondary_mid_status": mid.status,
        "date_added": mid.date_added.isoformat(),
        "txm_status": mid.txm_status,
    }


async def test_list(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids"
    )

    assert resp.status_code == status.HTTP_200_OK

    expected = await SecondaryMID.objects().get(SecondaryMID.pk == secondary_mid.pk)
    assert expected is not None
    assert resp.json() == [await secondary_mid_to_json(expected)]


async def test_list_deleted_secondary_mids(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    # create a deleted secondary MID that shouldn't be in the response
    await secondary_mid_factory(status=ResourceStatus.DELETED, merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids"
    )

    assert resp.status_code == status.HTTP_200_OK

    expected = await SecondaryMID.objects().get(SecondaryMID.pk == secondary_mid.pk)
    assert expected is not None
    assert resp.json() == [await secondary_mid_to_json(expected)]


async def test_list_on_plan(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
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


async def test_list_with_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/secondary_mids"
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_list_with_nonexistent_merchant(
    plan_factory: Factory[Plan],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/secondary_mids"
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_list_excluding_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    location_factory: Factory[Location],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
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


async def test_list_excluding_unlinked_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        params={"exclude_location": str(location.pk)},
    )

    assert resp.status_code == 200

    expected = await SecondaryMID.objects().get(SecondaryMID.pk == secondary_mid.pk)
    assert expected is not None
    assert resp.json() == [await secondary_mid_to_json(expected)]


async def test_list_excluding_nonexistent_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        params={"exclude_location": str(uuid4())},
    )

    assert_is_not_found_error(resp, loc=["query", "exclude_location"])


async def test_list_excluding_location_with_wrong_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory()

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        params={"exclude_location": str(location.pk)},
    )

    assert_is_not_found_error(resp, loc=["query", "exclude_location"])


async def test_details(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
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
    assert expected is not None
    assert resp.json() == await secondary_mid_to_json(expected)


async def test_details_noexistent_secondary_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/{uuid4()}"
    )
    assert_is_not_found_error(resp, loc=["path", "secondary_mid_ref"])


async def test_details_with_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/secondary_mids/{secondary_mid.pk}"
    )
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_details_with_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/secondary_mids/{secondary_mid.pk}"
    )
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_create_without_onboarding(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_slug": default_payment_schemes[0].slug,
                "secondary_mid": mid.secondary_mid,
                "payment_scheme_store_name": mid.payment_scheme_store_name,
                "payment_enrolment_status": mid.payment_enrolment_status,
            },
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED

    mid_ref = resp.json()["secondary_mid_ref"]
    expected = await SecondaryMID.objects().where(SecondaryMID.pk == mid_ref).first()
    assert expected is not None
    assert resp.json() == await secondary_mid_to_json(expected)

    # TODO: uncomment when harmonia supports onboarding secondary MIOs.
    # assert not await Job.exists().where(
    #     Job.message_type == OnboardSecondaryMIDs.__name__,
    #     Job.message
    #     == OnboardSecondaryMIDs(secondary_mid_refs=[secondary_mid_ref]).dict(),
    # )


async def test_create_and_onboard(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        json={
            "onboard": True,
            "secondary_mid_metadata": {
                "payment_scheme_slug": default_payment_schemes[0].slug,
                "secondary_mid": mid.secondary_mid,
                "payment_scheme_store_name": mid.payment_scheme_store_name,
                "payment_enrolment_status": mid.payment_enrolment_status,
            },
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED

    mid_ref = resp.json()["secondary_mid_ref"]

    expected = await SecondaryMID.objects().where(SecondaryMID.pk == mid_ref).first()
    assert expected is not None
    assert resp.json() == await secondary_mid_to_json(expected)

    # TODO: uncomment when harmonia supports secondary MID onboarding.
    # assert await Job.exists().where(
    #     Job.message_type == OnboardSecondaryMIDs.__name__,
    #     Job.message == OnboardSecondaryMIDs(secondary_mid_refs=[secondary_mid_ref]).dict(),
    # )


async def test_create_without_payment_scheme_store_name(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_slug": default_payment_schemes[0].slug,
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
    assert expected is not None
    assert resp.json() == await secondary_mid_to_json(expected)


async def test_create_with_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/secondary_mids",
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_slug": default_payment_schemes[0].slug,
                "secondary_mid": mid.secondary_mid,
                "payment_scheme_store_name": mid.payment_scheme_store_name,
                "payment_enrolment_status": mid.payment_enrolment_status,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


# @test("can't create a secondary MID on a merchant that does not exist")
async def test_create_with_nonexistent_merchant(
    plan_factory: Factory[Plan],
    secondary_mid_factory: Factory[SecondaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/secondary_mids",
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_slug": default_payment_schemes[0].slug,
                "secondary_mid": mid.secondary_mid,
                "payment_scheme_store_name": mid.payment_scheme_store_name,
                "payment_enrolment_status": mid.payment_enrolment_status,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_create_duplication_value(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    existing_mid = await secondary_mid_factory()
    merchant = await merchant_factory(plan=plan)
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_slug": default_payment_schemes[0].slug,
                "secondary_mid": existing_mid.secondary_mid,
                "payment_scheme_store_name": new_mid.payment_scheme_store_name,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_uniqueness_error(
        resp, loc=["body", "secondary_mid_metadata", "secondary_mid"]
    )


async def test_create_without_payment_scheme_slug(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
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
        resp, loc=["body", "secondary_mid_metadata", "payment_scheme_slug"]
    )


async def test_create_with_null_payment_scheme_slug(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_slug": None,
                "secondary_mid": new_mid.secondary_mid,
                "payment_scheme_store_name": new_mid.payment_scheme_store_name,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_null_error(
        resp, loc=["body", "secondary_mid_metadata", "payment_scheme_slug"]
    )


async def test_create_with_invalid_payment_scheme_slug(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_slug": "bad",
                "secondary_mid": new_mid.secondary_mid,
                "payment_scheme_store_name": new_mid.payment_scheme_store_name,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_not_found_error(
        resp, loc=["body", "secondary_mid_metadata", "payment_scheme_slug"]
    )


async def test_create_without_value(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_slug": default_payment_schemes[0].slug,
                "payment_scheme_store_name": new_mid.payment_scheme_store_name,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_missing_field_error(
        resp, loc=["body", "secondary_mid_metadata", "secondary_mid"]
    )


async def test_create_with_null_value(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    new_mid = await secondary_mid_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids",
        json={
            "onboard": False,
            "secondary_mid_metadata": {
                "payment_scheme_slug": default_payment_schemes[0].slug,
                "secondary_mid": None,
                "payment_scheme_store_name": new_mid.payment_scheme_store_name,
                "payment_enrolment_status": new_mid.payment_enrolment_status,
            },
        },
    )

    assert_is_null_error(resp, loc=["body", "secondary_mid_metadata", "secondary_mid"])


async def test_delete(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
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


async def test_delete_with_location_link(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    secondary_mid_factory: Factory[SecondaryMID],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    location = await location_factory(merchant=merchant)
    await secondary_mid_location_link_factory(
        secondary_mid=secondary_mid, location=location
    )
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/deletion",
        json={"secondary_mid_refs": [str(secondary_mid.pk)]},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert not await SecondaryMIDLocationLink.exists().where(
        SecondaryMIDLocationLink.secondary_mid == secondary_mid
    )


async def test_delete_not_onboarded(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
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

    expected = (
        await SecondaryMID.all_select(SecondaryMID.status)
        .where(SecondaryMID.pk == mid.pk)
        .first()
    )
    assert expected is not None
    mid_status = expected["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert mid_status == ResourceStatus.DELETED

    # TODO: uncomment once harmonia supports secondary MID offboarding.
    # assert not await Job.exists().where(
    #     Job.message_type == OffboardAndDeleteSecondaryMIDs.__name__,
    #     Job.message == OffboardAndDeleteSecondaryMIDs(secondary_mid_refs=[secondary_mid.pk]).dict(),
    # )


async def test_delete_offboarded(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
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

    expected = (
        await SecondaryMID.all_select(SecondaryMID.status)
        .where(SecondaryMID.pk == mid.pk)
        .first()
    )
    assert expected is not None
    mid_status = expected["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert mid_status == ResourceStatus.DELETED

    # TODO: uncomment once harmonia supports secondary MID offboarding.
    # assert not await Job.exists().where(
    #     Job.message_type == OffboardAndDeleteSecondaryMIDs.__name__,
    #     Job.message == OffboardAndDeleteSecondaryMIDs(secondary_mid_refs=[secondary_mid.pk]).dict(),
    # )


async def test_delete_onboarded(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await secondary_mid_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/deletion",
        json={"secondary_mid_refs": [str(mid.pk)]},
    )

    expected = (
        await SecondaryMID.select(SecondaryMID.status)
        .where(SecondaryMID.pk == mid.pk)
        .first()
    )
    assert expected is not None
    mid_status = expected["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert mid_status == ResourceStatus.PENDING_DELETION

    # TODO: uncomment once harmonia supports secondary MID onboarding.
    # assert await Job.exists().where(
    #     Job.message_type == OffboardAndDeleteSecondaryMIDs.__name__,
    #     Job.message == OffboardAndDeleteSecondaryMIDs(secondary_mid_refs=[secondary_mid.pk]).dict(),
    # )


async def test_delete_nonexistent_secondary_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/deletion",
        json={"secondary_mid_refs": [str(uuid4())]},
    )

    assert_is_not_found_error(resp, loc=["body", "secondary_mid_refs"])


async def test_delete_zero_secondary_mids(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/deletion",
        json={"secondary_mid_refs": []},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == []


async def test_associate_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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
    assert link is not None
    assert resp.json() == [
        {
            "link_ref": str(link["pk"]),
            "location_ref": str(location.pk),
            "location_title": location.display_text,
        }
    ]


async def test_associate_location_wrong_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    location = await location_factory()

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/{secondary_mid.pk}/secondary_mid_location_links",
        json={"location_refs": [str(location.pk)]},
    )

    assert_is_not_found_error(resp, loc=["body", "location_ref"])


async def test_associate_location_with_nonexistent_secondary_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/secondary_mids/{uuid4()}/secondary_mid_location_links",
        json={"location_refs": [str(location.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "secondary_mid_ref"])


async def test_associate_location_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    location = await location_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/secondary_mids/{secondary_mid.pk}/secondary_mid_location_links",
        json={"location_refs": [str(location.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_associate_location_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    location = await location_factory(merchant=merchant)

    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/secondary_mids/{secondary_mid.pk}/secondary_mid_location_links",
        json={"location_refs": [str(location.pk)]},
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_associate_same_location_twice(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    location_factory: Factory[Location],
    test_client: TestClient,
) -> None:
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


async def test_associated_locations(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    location_factory: Factory[Location],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
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
            "location_title": location.display_text,
        }
    ]


async def test_associated_locations_with_nonexistent_secondary_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    location_factory: Factory[Location],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
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


async def test_associated_locations_with_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    location_factory: Factory[Location],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
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


async def test_associated_locations_with_nonexistent_plan(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    location_factory: Factory[Location],
    secondary_mid_location_link_factory: Factory[SecondaryMIDLocationLink],
    test_client: TestClient,
) -> None:
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
