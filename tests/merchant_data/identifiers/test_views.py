"""Tests for identifier API endpoints."""
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from qbert.tables import Job
from ward import skip, test

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.merchants.tables import Merchant
from tests.fixtures import auth_header, test_client
from tests.helpers import assert_is_not_found_error
from tests.merchant_data.factories import identifier, identifier_factory, merchant


@test("can delete an identifier")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    identifier: Identifier = identifier,
) -> None:
    merchant = await identifier.get_related(Identifier.merchant)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers/deletion",
        headers=auth_header,
        json=[str(identifier.pk)],
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {
        "identifiers": [
            {
                "identifier_ref": str(identifier.pk),
                "status": (
                    "pending_deletion"
                    if identifier.txm_status == TXMStatus.ONBOARDED
                    else "deleted"
                ),
            }
        ]
    }


@test("an identifier that is not onboarded is deleted and no qbert job is created")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    identifier = await identifier_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers/deletion",
        headers=auth_header,
        json=[str(identifier.pk)],
    )

    identifier_status = (
        await Identifier.select(Identifier.status)
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


@test("an identifier that is offboarded is deleted and no qbert job is created")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    identifier = await identifier_factory(
        merchant=merchant, txm_status=TXMStatus.OFFBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers/deletion",
        headers=auth_header,
        json=[str(identifier.pk)],
    )

    identifier_status = (
        await Identifier.select(Identifier.status)
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


@test(
    "an identifier that is onboarded goes to pending deletion and a qbert job is created"
)
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    identifier = await identifier_factory(
        merchant=merchant, txm_status=TXMStatus.ONBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers/deletion",
        headers=auth_header,
        json=[str(identifier.pk)],
    )

    identifier_status = (
        await Identifier.select(Identifier.status)
        .where(Identifier.pk == identifier.pk)
        .first()
    )["status"]

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert identifier_status == ResourceStatus.PENDING_DELETION

    # TODO: uncomment once harmonia supports identifier/PSIMI onboarding.
    # assert await Job.exists().where(
    #     Job.message_type == OffboardAndDeleteIdentifiers.__name__,
    #     Job.message == OffboardAndDeleteIdentifiers(identifier_refs=[identifier.pk]).dict(),
    # )


@test("deleting an identifier that doesn't exist returns a useful error")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers/deletion",
        headers=auth_header,
        json=[str(uuid4())],
    )

    assert_is_not_found_error(resp, loc=["body", "identifier_refs"])


@test("sending a delete identifiers request with an empty body does nothing")
def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchant: Merchant = merchant,
) -> None:
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers/deletion",
        headers=auth_header,
        json=[],
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {"identifiers": []}
