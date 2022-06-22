"""Tests for the secondary MIDs database layer."""

from datetime import timezone
from uuid import uuid4

from ward import raises, test

from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.secondary_mids.db import get_secondary_mid
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from tests.fixtures import database
from tests.merchant_data.factories import (
    merchant_factory,
    plan_factory,
    secondary_mid_factory,
)


@test("can get a secondary MID")
async def _(_db: None = database) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    mid = await secondary_mid_factory(merchant=merchant)
    mid = await SecondaryMID.objects().get(SecondaryMID.pk == mid.pk)
    payment_scheme_code = (
        await PaymentScheme.select(PaymentScheme.code)
        .where(PaymentScheme.slug == mid.payment_scheme)
        .first()
    )["code"]
    actual = await get_secondary_mid(mid.pk, plan_ref=plan.pk, merchant_ref=merchant.pk)
    assert actual == {
        "date_added": mid.date_added.replace(tzinfo=timezone.utc),
        "payment_enrolment_status": mid.payment_enrolment_status,
        "payment_scheme.code": payment_scheme_code,
        "payment_scheme_store_name": mid.payment_scheme_store_name,
        "pk": mid.pk,
        "secondary_mid": mid.secondary_mid,
        "status": mid.status,
        "txm_status": mid.txm_status,
    }


@test("attempting to get a non-existent secondary MID raises NoSuchRecord")
async def _(_db: None = database) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory()
    with raises(NoSuchRecord):
        await get_secondary_mid(uuid4(), plan_ref=plan.pk, merchant_ref=merchant.pk)


@test(
    "attempting to get a secondary MID from a non-existent merchant raises NoSuchRecord"
)
async def _(_db: None = database) -> None:
    plan = await plan_factory()
    with raises(NoSuchRecord):
        await get_secondary_mid(uuid4(), plan_ref=plan.pk, merchant_ref=uuid4())


@test("attempting to get a secondary MID from a non-existent plan raises NoSuchRecord")
async def _(_db: None = database) -> None:
    merchant = await merchant_factory()
    with raises(NoSuchRecord):
        await get_secondary_mid(uuid4(), plan_ref=uuid4(), merchant_ref=merchant.pk)
