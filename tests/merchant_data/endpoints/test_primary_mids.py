"""Test merchant data API endpoints that operate on primary MIDs."""
import random
from operator import itemgetter

from fastapi.testclient import TestClient
from ward import test

from bullsquid.merchant_data.tables import Merchant, PaymentScheme, Plan, PrimaryMID
from tests.factories import primary_mid, primary_mid_factory, three_merchants
from tests.fixtures import auth_header, database, test_client


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
        "date_added": primary_mid.date_added.isoformat(),
        "txm_status": primary_mid.txm_status,
    }


@test("can list primary mids")
async def _(
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    primary_mid: PrimaryMID = primary_mid,
) -> None:
    # work around a bug in piccolo's ModelBuilder that returns datetimes without timezones
    primary_mid = await PrimaryMID.objects().get(PrimaryMID.pk == primary_mid.pk)

    merchant_ref, plan_ref = itemgetter("merchant", "merchant.plan")(
        await PrimaryMID.select(
            PrimaryMID.merchant,
            PrimaryMID.merchant.plan,
        )
        .where(PrimaryMID.pk == primary_mid.pk)
        .first()
    )

    resp = test_client.get(
        f"/api/v1/plans/{plan_ref}/merchants/{merchant_ref}/mids", headers=auth_header
    )

    assert resp.ok, resp.json()
    assert resp.json() == {"mids": [await primary_mid_to_json(primary_mid)]}


@test("can list primary mids from a specific plan")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
    merchants: list[Merchant] = three_merchants,
) -> None:
    for merchant in merchants:
        for _ in range(random.randint(1, 3)):
            await primary_mid_factory(merchant=merchant)

    plan_ref = (await Plan.select(Plan.pk).where(Plan.pk == merchants[0].plan).first())[
        "pk"
    ]

    resp = test_client.get(
        f"/api/v1/plans/{plan_ref}/merchants/{merchants[0].pk}/mids",
        headers=auth_header,
    )

    expected = await PrimaryMID.objects().where(PrimaryMID.merchant == merchants[0])

    assert resp.ok, resp.json()
    assert resp.json() == {
        "mids": [await primary_mid_to_json(primary_mid) for primary_mid in expected]
    }
