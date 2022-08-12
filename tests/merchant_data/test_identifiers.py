"""Tests for identifier API endpoints."""
import random
from operator import itemgetter
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from ward import test

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.merchants.models import MerchantPaymentSchemeCountResponse
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from tests.fixtures import database, test_client
from tests.helpers import (
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_null_error,
    assert_is_uniqueness_error,
)
from tests.merchant_data.factories import (
    default_payment_schemes,
    identifier_factory,
    merchant_factory,
    plan_factory,
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


@test("can list identifiers")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    identifier = await identifier_factory()
    # work around a bug in piccolo's ModelBuilder that returns datetimes without timezones
    identifier = await Identifier.objects().get(Identifier.pk == identifier.pk)

    merchant_ref, plan_ref = itemgetter("merchant", "merchant.plan")(
        await Identifier.select(
            Identifier.merchant,
            Identifier.merchant.plan,
        )
        .where(Identifier.pk == identifier.pk)
        .first()
    )

    resp = test_client.get(
        f"/api/v1/plans/{plan_ref}/merchants/{merchant_ref}/identifiers"
    )

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [await identifier_to_json(identifier)]


@test("deleted identifiers are not listed")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    identifier = await identifier_factory()
    # work around a bug in piccolo's ModelBuilder that returns datetimes without timezones
    identifier = await Identifier.objects().get(Identifier.pk == identifier.pk)

    merchant_ref, plan_ref = itemgetter("merchant", "merchant.plan")(
        await Identifier.select(
            Identifier.merchant,
            Identifier.merchant.plan,
        )
        .where(Identifier.pk == identifier.pk)
        .first()
    )

    # create a deleted identifier that shouldn't be in the response
    await identifier_factory(status=ResourceStatus.DELETED, merchant=merchant_ref)

    resp = test_client.get(
        f"/api/v1/plans/{plan_ref}/merchants/{merchant_ref}/identifiers",
    )

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [await identifier_to_json(identifier)]


@test("can list identifiers from a specific plan")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchants = [await merchant_factory() for _ in range(3)]
    for merchant in merchants:
        for _ in range(random.randint(1, 3)):
            await identifier_factory(merchant=merchant)

    plan_ref = (await Plan.select(Plan.pk).where(Plan.pk == merchants[0].plan).first())[
        "pk"
    ]

    resp = test_client.get(
        f"/api/v1/plans/{plan_ref}/merchants/{merchants[0].pk}/identifiers",
    )

    expected = await Identifier.objects().where(Identifier.merchant == merchants[0])

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == [
        await identifier_to_json(identifier) for identifier in expected
    ]


@test("can't list identifiers on a plan that doesn't exist")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/identifiers",
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can't list identifiers on a merchant that doesn't exist")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/identifiers",
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can get identifier details")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
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


@test("can't get identifier details from a non-existent identifier")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{merchant.pk}/identifiers/{uuid4()}",
    )
    assert_is_not_found_error(resp, loc=["path", "identifier_ref"])


@test("can't get identifier details from a non-existent merchant")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    identifier = await identifier_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/identifiers/{identifier.pk}",
    )
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't get identifier details from a non-existent plan")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    identifier = await identifier_factory(merchant=merchant)
    resp = test_client.get(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/identifiers/{identifier.pk}",
    )
    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can create an identifier on a merchant without onboarding")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory()
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "value": identifier.value,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
                "payment_scheme_code": payment_schemes[0].code,
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


@test("can create and onboard an identifier on a merchant")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory()
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": True,
            "identifier_metadata": {
                "value": identifier.value,
                "payment_scheme_code": payment_schemes[0].code,
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


@test("can't create an identifier on a plan that does not exist")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory()
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{uuid4()}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "value": identifier.value,
                "payment_scheme_code": payment_schemes[0].code,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "plan_ref"])


@test("can't create an identifier on a merchant that does not exist")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    plan = await plan_factory()
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{plan.pk}/merchants/{uuid4()}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "value": identifier.value,
                "payment_scheme_code": payment_schemes[0].code,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


@test("can't create an identifier with a value that already exists")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    existing_identifier = await identifier_factory()
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory()
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "value": existing_identifier.value,
                "payment_scheme_code": payment_schemes[0].code,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_uniqueness_error(resp, loc=["body", "identifier_metadata", "value"])


@test("can't create an identifier with a missing payment scheme code")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers",
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


@test("can't create an identifier with a null payment scheme code")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers",
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


@test("can't create an identifier with a missing value")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory()
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_missing_field_error(resp, loc=["body", "identifier_metadata", "value"])


@test("can't create an identifier with a null value")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    payment_schemes = await default_payment_schemes()
    merchant = await merchant_factory()
    identifier = await identifier_factory(persist=False)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers",
        json={
            "onboard": False,
            "identifier_metadata": {
                "payment_scheme_code": payment_schemes[0].code,
                "value": None,
                "payment_scheme_merchant_name": identifier.payment_scheme_merchant_name,
            },
        },
    )

    assert_is_null_error(resp, loc=["body", "identifier_metadata", "value"])


@test("can delete an identifier")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    identifier = await identifier_factory()
    merchant = await identifier.get_related(Identifier.merchant)
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers/deletion",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    identifier = await identifier_factory(
        merchant=merchant, txm_status=TXMStatus.NOT_ONBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers/deletion",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    identifier = await identifier_factory(
        merchant=merchant, txm_status=TXMStatus.OFFBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers/deletion",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    identifier = await identifier_factory(
        merchant=merchant, txm_status=TXMStatus.ONBOARDED
    )

    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers/deletion",
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
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers/deletion",
        json=[str(uuid4())],
    )

    assert_is_not_found_error(resp, loc=["body", "identifier_refs"])


@test("sending a delete identifiers request with an empty body does nothing")
async def _(
    _: None = database,
    test_client: TestClient = test_client,
) -> None:
    merchant = await merchant_factory()
    resp = test_client.post(
        f"/api/v1/plans/{merchant.plan}/merchants/{merchant.pk}/identifiers/deletion",
        json=[],
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.json() == {"identifiers": []}
