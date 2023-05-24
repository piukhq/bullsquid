"""Tests for PSIMI API endpoints."""
import random
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from qbert.tables import Job

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.psimis.tables import PSIMI
from bullsquid.merchant_data.tasks import (
    OffboardAndDeletePSIMIs,
    OffboardPSIMIs,
    OnboardPSIMIs,
    run_worker,
)
from tests.helpers import (
    Factory,
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_null_error,
    assert_is_uniqueness_error,
)


async def psimi_to_json(psimi: PSIMI) -> dict:
    """Converts a PSIMI to its expected JSON representation."""
    return {
        "psimi_ref": str(psimi.pk),
        "psimi_metadata": {
            "value": psimi.value,
            "payment_scheme_merchant_name": psimi.payment_scheme_merchant_name,
            "payment_scheme_slug": psimi.payment_scheme,
        },
        "psimi_status": psimi.status,
        "date_added": psimi.date_added.isoformat(),
    }


async def test_list(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(merchant=merchant)

    resp = test_client.get(f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis")

    assert resp.status_code == status.HTTP_200_OK

    expected = await PSIMI.objects().get(PSIMI.pk == psimi.pk)
    assert expected is not None
    assert resp.json() == [await psimi_to_json(expected)]


async def test_list_deleted_psimis(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(merchant=merchant)

    # create a deleted PSIMI that shouldn't be in the response
    await psimi_factory(status=ResourceStatus.DELETED, merchant=merchant.pk)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis",
    )

    assert resp.status_code == status.HTTP_200_OK

    expected = await PSIMI.objects().get(PSIMI.pk == psimi.pk)
    assert expected is not None
    assert resp.json() == [await psimi_to_json(expected)]


async def test_list_from_plan(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchants = [await merchant_factory(plan=plan) for _ in range(3)]
    for merchant in merchants:
        for _ in range(random.randint(1, 3)):
            await psimi_factory(merchant=merchant)

    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchants[0].pk}/psimis",
    )

    expected = await PSIMI.objects().where(PSIMI.merchant == merchants[0])

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [await psimi_to_json(psimi) for psimi in expected]


async def test_list_from_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/psimis",
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_list_from_nonexistent_merchant(
    plan_factory: Factory[Plan],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/psimis",
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_details(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/{psimi.pk}",
    )

    assert resp.status_code == status.HTTP_200_OK, resp.json()

    psimi_ref = resp.json()["psimi_ref"]
    expected = await PSIMI.objects().where(PSIMI.pk == psimi_ref).first()
    assert expected is not None
    assert resp.json() == await psimi_to_json(expected)


async def test_details_nonexistent_psimi(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/{uuid4()}",
    )
    assert_is_not_found_error(resp, loc=["path", "psimi_ref"])


async def test_details_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/psimis/{psimi.pk}",
    )
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_details_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    psimi = await psimi_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/psimis/{psimi.pk}",
    )
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_create_without_onboarding(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis",
        json={
            "onboard": False,
            "psimi_metadata": {
                "value": psimi.value,
                "payment_scheme_merchant_name": psimi.payment_scheme_merchant_name,
                "payment_scheme_slug": default_payment_schemes[0].slug,
            },
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED

    psimi_ref = resp.json()["psimi_ref"]

    expected = await PSIMI.objects().where(PSIMI.pk == psimi_ref).first()
    assert expected is not None
    assert resp.json() == await psimi_to_json(expected)

    assert not await Job.exists().where(
        Job.message_type == OnboardPSIMIs.__name__,
        Job.message == OnboardPSIMIs(psimi_refs=[psimi_ref]).dict(),
    )


async def test_create_and_onboard(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis",
        json={
            "onboard": True,
            "psimi_metadata": {
                "value": psimi.value,
                "payment_scheme_slug": default_payment_schemes[0].slug,
                "payment_scheme_merchant_name": psimi.payment_scheme_merchant_name,
            },
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED

    psimi_ref = resp.json()["psimi_ref"]

    expected = await PSIMI.objects().where(PSIMI.pk == psimi_ref).first()
    assert expected is not None
    assert resp.json() == await psimi_to_json(expected)

    assert await Job.exists().where(
        Job.message_type == OnboardPSIMIs.__name__,
        Job.message == OnboardPSIMIs(psimi_refs=[psimi_ref]).dict(),
    )


async def test_create_on_nonexistent_plan(
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    merchant = await merchant_factory()
    psimi = await psimi_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/psimis",
        json={
            "onboard": False,
            "psimi_metadata": {
                "value": psimi.value,
                "payment_scheme_slug": default_payment_schemes[0].slug,
                "payment_scheme_merchant_name": psimi.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


async def test_create_on_nonexistent_merchant(
    plan_factory: Factory[Plan],
    psimi_factory: Factory[PSIMI],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    psimi = await psimi_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/psimis",
        json={
            "onboard": False,
            "psimi_metadata": {
                "value": psimi.value,
                "payment_scheme_slug": default_payment_schemes[0].slug,
                "payment_scheme_merchant_name": psimi.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


async def test_create_with_existing_value(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    existing_psimi = await psimi_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis",
        json={
            "onboard": False,
            "psimi_metadata": {
                "value": existing_psimi.value,
                "payment_scheme_slug": default_payment_schemes[0].slug,
                "payment_scheme_merchant_name": psimi.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_uniqueness_error(resp, loc=["body", "psimi_metadata", "value"])


async def test_create_with_missing_payment_scheme_slug(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis",
        json={
            "onboard": False,
            "psimi_metadata": {
                "value": psimi.value,
                "payment_scheme_merchant_name": psimi.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_missing_field_error(
        resp, loc=["body", "psimi_metadata", "payment_scheme_slug"]
    )


async def test_create_with_null_payment_scheme_slug(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis",
        json={
            "onboard": False,
            "psimi_metadata": {
                "value": psimi.value,
                "payment_scheme_slug": None,
                "payment_scheme_merchant_name": psimi.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_null_error(resp, loc=["body", "psimi_metadata", "payment_scheme_slug"])


async def test_create_without_value(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis",
        json={
            "onboard": False,
            "psimi_metadata": {
                "payment_scheme_slug": default_payment_schemes[0].slug,
                "payment_scheme_merchant_name": psimi.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_missing_field_error(resp, loc=["body", "psimi_metadata", "value"])


async def test_create_with_null_value(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    default_payment_schemes: list[PaymentScheme],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis",
        json={
            "onboard": False,
            "psimi_metadata": {
                "payment_scheme_slug": default_payment_schemes[0].slug,
                "value": None,
                "payment_scheme_merchant_name": psimi.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_null_error(resp, loc=["body", "psimi_metadata", "value"])


async def test_onboard(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/onboarding",
        json={"psimi_refs": [str(psimi.pk)]},
    )

    assert resp.status_code == status.HTTP_200_OK, resp.json()

    expected = await PSIMI.objects().get(PSIMI.pk == psimi.pk)
    assert expected is not None
    assert resp.json() == [await psimi_to_json(expected)]

    assert await Job.exists().where(
        Job.message_type == OnboardPSIMIs.__name__,
        Job.message == OnboardPSIMIs(psimi_refs=[psimi.pk]).dict(),
    )

    await run_worker(burst=True)
    expected = await PSIMI.objects().get(PSIMI.pk == psimi.pk)
    assert expected is not None
    assert expected.txm_status == TXMStatus.ONBOARDED


async def test_onboard_no_psimis(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/onboarding",
        json={"psimi_refs": []},
    )

    assert resp.status_code == status.HTTP_200_OK, resp.json()
    assert resp.json() == []
    print(await Job.select())
    assert not await Job.exists().where(Job.message_type == OnboardPSIMIs.__name__)


async def test_onboard_nonexistent_psimis(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/onboarding",
        json={"psimi_refs": [str(uuid4())]},
    )

    assert_is_not_found_error(resp, loc=["body", "psimi_refs"])


async def test_offboard(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/offboarding",
        json={"psimi_refs": [str(psimi.pk)]},
    )

    assert resp.status_code == status.HTTP_200_OK, resp.json()

    expected = await PSIMI.objects().get(PSIMI.pk == psimi.pk)
    assert expected is not None
    assert resp.json() == [await psimi_to_json(expected)]

    assert await Job.exists().where(
        Job.message_type == OffboardPSIMIs.__name__,
        Job.message == OffboardPSIMIs(psimi_refs=[psimi.pk]).dict(),
    )

    await run_worker(burst=True)
    expected = await PSIMI.objects().get(PSIMI.pk == psimi.pk)
    assert expected is not None
    assert expected.txm_status == TXMStatus.OFFBOARDED


async def test_offboard_no_psimis(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/offboarding",
        json={"psimi_refs": []},
    )

    assert resp.status_code == status.HTTP_200_OK, resp.json()
    assert resp.json() == []
    print(await Job.select())
    assert not await Job.exists().where(Job.message_type == OffboardPSIMIs.__name__)


async def test_offboard_nonexistent_psimis(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/offboarding",
        json={"psimi_refs": [str(uuid4())]},
    )

    assert_is_not_found_error(resp, loc=["body", "psimi_refs"])


async def test_delete(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(merchant=merchant)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/deletion",
        json={"psimi_refs": [str(psimi.pk)]},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == [
        {
            "psimi_ref": str(psimi.pk),
            "status": (
                "pending_deletion"
                if psimi.txm_status == TXMStatus.ONBOARDED
                else "deleted"
            ),
        }
    ]


async def test_delete_not_onboarded_psimi(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/deletion",
        json={"psimi_refs": [str(psimi.pk)]},
    )

    expected = await PSIMI.all_select(PSIMI.status).where(PSIMI.pk == psimi.pk).first()
    assert expected is not None
    psimi_status = expected["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert psimi_status == ResourceStatus.DELETED

    assert not await Job.exists().where(
        Job.message_type == OffboardAndDeletePSIMIs.__name__,
        Job.message == OffboardAndDeletePSIMIs(psimi_refs=[psimi.pk]).dict(),
    )


async def test_delete_offboarded_psimi(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(merchant=merchant, txm_status=TXMStatus.OFFBOARDED)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/deletion",
        json={"psimi_refs": [str(psimi.pk)]},
    )

    expected = await PSIMI.all_select(PSIMI.status).where(PSIMI.pk == psimi.pk).first()
    assert expected is not None
    psimi_status = expected["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert psimi_status == ResourceStatus.DELETED

    assert not await Job.exists().where(
        Job.message_type == OffboardAndDeletePSIMIs.__name__,
        Job.message == OffboardAndDeletePSIMIs(psimi_refs=[psimi.pk]).dict(),
    )


async def test_delete_onboarded_psimi(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    psimi_factory: Factory[PSIMI],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await psimi_factory(merchant=merchant, txm_status=TXMStatus.ONBOARDED)

    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/deletion",
        json={"psimi_refs": [str(psimi.pk)]},
    )

    expected = await PSIMI.select(PSIMI.status).where(PSIMI.pk == psimi.pk).first()
    assert expected is not None
    psimi_status = expected["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    assert psimi_status == ResourceStatus.PENDING_DELETION

    assert await Job.exists().where(
        Job.message_type == OffboardAndDeletePSIMIs.__name__,
        Job.message == OffboardAndDeletePSIMIs(psimi_refs=[psimi.pk]).dict(),
    )


async def test_delete_nonexistent_psimi(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/deletion",
        json={"psimi_refs": [str(uuid4())]},
    )

    assert_is_not_found_error(resp, loc=["body", "psimi_refs"])


async def test_delete_no_refs(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/psimis/deletion",
        json={"psimi_refs": []},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == []
