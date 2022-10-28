"""Tests for identifier API endpoints."""
import random
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from tests.helpers import (
    Factory,
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_null_error,
    assert_is_uniqueness_error,
)


async def identifier_to_json(identifier: Identifier) -> dict:
    """Converts an identifier to its expected JSON representation."""
    payment_scheme_code = (
        await PaymentScheme.select(PaymentScheme.code)
        .where(PaymentScheme.slug == identifier.payment_scheme)
        .first()
    )["code"]

    return {
        "identifier_ref": str(identifier.pk),
        "identifier_metadata": {
            "value": identifier.value,
            "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            "payment_scheme_code": payment_scheme_code,
        },
        "identifier_status": identifier.status,
        "date_added": identifier.date_added.isoformat(),
    }


async def test_list(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers"
    )

    assert resp.status_code == status.HTTP_200_OK

    identifier = await Identifier.objects().get(Identifier.pk == identifier.pk)
    assert resp.json() == [await identifier_to_json(identifier)]


async def test_list_deleted_identifiers(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(merchant=merchant)

    # create a deleted identifier that shouldn't be in the response
    await identifier_factory(status=ResourceStatus.DELETED, merchant=merchant.pk)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers",
    )

    assert resp.status_code == status.HTTP_200_OK

    identifier = await Identifier.objects().get(Identifier.pk == identifier.pk)
    assert resp.json() == [await identifier_to_json(identifier)]


async def test_list_from_plan(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchants = [await merchant_factory(plan=plan) for _ in range(3)]
    for merchant in merchants:
        for _ in range(random.randint(1, 3)):
            await identifier_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchants[0].pk}/identifiers",
    )

    expected = await Identifier.objects().where(Identifier.merchant == merchants[0])

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [
        await identifier_to_json(identifier) for identifier in expected
    ]


async def test_list_from_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/identifiers",
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_list_from_nonexistent_merchant(
    plan_factory: Factory[Plan],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/identifiers",
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_details(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers/{identifier.pk}",
    )

    assert resp.status_code == status.HTTP_200_OK, resp.json()

    identifier_ref = resp.json()["identifier_ref"]
    expected = await Identifier.objects().where(Identifier.pk == identifier_ref).first()
    assert resp.json() == await identifier_to_json(expected)


async def test_details_nonexistent_identifier(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers/{uuid4()}",
    )
    assert_is_not_found_error(resp, loc=["path", "identifier_ref"])


async def test_details_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/identifiers/{identifier.pk}",
    )
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_details_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    identifier = await identifier_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/identifiers/{identifier.pk}",
    )
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_create_without_onboarding(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "value": identifier.value,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
                "payment_scheme_code": default_payment_schemes[0].code,
            },
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED

    identifier_ref = resp.json()["identifier_ref"]

    expected = await Identifier.objects().where(Identifier.pk == identifier_ref).first()
    assert resp.json() == await identifier_to_json(expected)

    # TODO: uncomment when Harmonia supports identifier onboarding.
    # assert not await Job.exists().where(
    #     Job.message_type == OnboardIdentifiers.__name__,
    #     Job.message == OnboardIdentifiers(identifier_refs=[identifier_ref]).dict(),
    # )


async def test_create_and_onboard(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": True,
            "identifier_metadata": {
                "value": identifier.value,
                "payment_scheme_code": default_payment_schemes[0].code,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            },
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED

    identifier_ref = resp.json()["identifier_ref"]

    expected = await Identifier.objects().where(Identifier.pk == identifier_ref).first()
    assert resp.json() == await identifier_to_json(expected)

    # TODO: uncomment when Harmonia supports identifier onboarding.
    # assert await Job.exists().where(
    #     Job.message_type == OnboardIdentifiers.__name__,
    #     Job.message == OnboardIdentifiers(identifier_refs=[identifier_ref]).dict(),
    # )


async def test_create_on_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "value": identifier.value,
                "payment_scheme_code": default_payment_schemes[0].code,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_create_on_nonexistent_merchant(
    plan_factory: Factory[Plan],
    identifier_factory: Factory[Identifier],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "value": identifier.value,
                "payment_scheme_code": default_payment_schemes[0].code,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_create_with_existing_value(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    existing_identifier = await identifier_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "value": existing_identifier.value,
                "payment_scheme_code": default_payment_schemes[0].code,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_uniqueness_error(resp, loc=["body", "identifier_metadata", "value"])


async def test_create_with_missing_payment_scheme_code(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "value": identifier.value,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_missing_field_error(
        resp, loc=["body", "identifier_metadata", "payment_scheme_code"]
    )


async def test_create_with_null_payment_scheme_code(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "value": identifier.value,
                "payment_scheme_code": None,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_null_error(
        resp, loc=["body", "identifier_metadata", "payment_scheme_code"]
    )


async def test_create_without_value(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "payment_scheme_code": default_payment_schemes[0].code,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_missing_field_error(resp, loc=["body", "identifier_metadata", "value"])


async def test_create_with_null_value(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "payment_scheme_code": default_payment_schemes[0].code,
                "value": None,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_null_error(resp, loc=["body", "identifier_metadata", "value"])


async def test_delete(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(merchant=merchant)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers/deletion",
        json={"identifier_refs": [str(identifier.pk)]},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == [
        {
            "identifier_ref": str(identifier.pk),
            "status": (
                "pending_deletion"
                if identifier.txm_status == TXMStatus.ONBOARDED
                else "deleted"
            ),
        }
    ]


async def test_delete_not_onboarded_identifier(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers/deletion",
        json={"identifier_refs": [str(identifier.pk)]},
    )

    identifier_status = (
        await Identifier.all_select(Identifier.status)
        .where(Identifier.pk == identifier.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert identifier_status == ResourceStatus.DELETED

    # TODO: uncomment once harmonia supports identifier/PSIMI offboarding.
    # assert not await Job.exists().where(
    #     Job.message_type == OffboardAndDeleteIdentifiers.__name__,
    #     Job.message == OffboardAndDeleteIdentifiers(identifier_refs=[identifier.pk]).dict(),
    # )


async def test_delete_offboarded_identifier(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(
        merchant=merchant, txm_status=TXMStatus.OFFBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers/deletion",
        json={"identifier_refs": [str(identifier.pk)]},
    )

    identifier_status = (
        await Identifier.all_select(Identifier.status)
        .where(Identifier.pk == identifier.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert identifier_status == ResourceStatus.DELETED

    # TODO: uncomment once harmonia supports identifier/PSIMI offboarding.
    # assert not await Job.exists().where(
    #     Job.message_type == OffboardAndDeleteIdentifiers.__name__,
    #     Job.message == OffboardAndDeleteIdentifiers(identifier_refs=[identifier.pk]).dict(),
    # )


async def test_delete_onboarded_identifier(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(
        merchant=merchant, txm_status=TXMStatus.ONBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers/deletion",
        json={"identifier_refs": [str(identifier.pk)]},
    )

    identifier_status = (
        await Identifier.select(Identifier.status)
        .where(Identifier.pk == identifier.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    assert identifier_status == ResourceStatus.PENDING_DELETION

    # TODO: uncomment once harmonia supports identifier/PSIMI onboarding.
    # assert await Job.exists().where(
    #     Job.message_type == OffboardAndDeleteIdentifiers.__name__,
    #     Job.message == OffboardAndDeleteIdentifiers(identifier_refs=[identifier.pk]).dict(),
    # )


async def test_delete_nonexistent_identifier(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers/deletion",
        json={"identifier_refs": [str(uuid4())]},
    )

    assert_is_not_found_error(resp, loc=["body", "identifier_refs"])


async def test_delete_no_refs(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers/deletion",
        json={"identifier_refs": []},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == []
