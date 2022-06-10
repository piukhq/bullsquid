"""Tests for secondary MID API endpoints."""
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from ward import test

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from tests.factories import merchant, secondary_mid, secondary_mid_factory
from tests.fixtures import auth_header, test_client
from tests.helpers import assert_is_not_found_error


@test("can delete a secondary MID")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    secondary_mid: SecondaryMID = secondary_mid,
) -> None:
    merchant = await secondary_mid.get_related(SecondaryMID.merchant)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids/deletion",
        headers=auth_header,
        json=[str(secondary_mid.pk)],
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {
        "secondary_mids": [
            {
                "secondary_mid_ref": str(secondary_mid.pk),
                "status": (
                    "pending_deletion"
                    if secondary_mid.txm_status == TXMStatus.ONBOARDED
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
    secondary_mid = await secondary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids/deletion",
        headers=auth_header,
        json=[str(secondary_mid.pk)],
    )

    secondary_mid_status = (
        await SecondaryMID.select(SecondaryMID.status)
        .where(SecondaryMID.pk == secondary_mid.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert secondary_mid_status == ResourceStatus.DELETED

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
    secondary_mid = await secondary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.OFFBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids/deletion",
        headers=auth_header,
        json=[str(secondary_mid.pk)],
    )

    secondary_mid_status = (
        await SecondaryMID.select(SecondaryMID.status)
        .where(SecondaryMID.pk == secondary_mid.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert secondary_mid_status == ResourceStatus.DELETED

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
    secondary_mid = await secondary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.ONBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/secondary_mids/deletion",
        headers=auth_header,
        json=[str(secondary_mid.pk)],
    )

    secondary_mid_status = (
        await SecondaryMID.select(SecondaryMID.status)
        .where(SecondaryMID.pk == secondary_mid.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert secondary_mid_status == ResourceStatus.PENDING_DELETION

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
