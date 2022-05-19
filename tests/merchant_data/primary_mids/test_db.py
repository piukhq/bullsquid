"""Test primary MIDs database access layer."""
from datetime import timezone

from pydantic import MissingDiscriminator
from ward import test

from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.primary_mids.db import list_primary_mids
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from tests.factories import merchant, primary_mid_factory


@test("can list primary mids")
async def _(merchant: Merchant = merchant) -> None:
    primary_mids = [await primary_mid_factory(merchant=merchant) for _ in range(3)]

    async def payment_scheme_code(mid: PrimaryMID) -> int:
        result = (
            await PaymentScheme.select(PaymentScheme.code)
            .where(PaymentScheme.slug == mid.payment_scheme)
            .first()
        )
        return result["code"]

    # modelbuilder returns naive datetimes instead of tz-aware.
    # reloading the instances like this fixes that.
    primary_mids = [
        await PrimaryMID.objects().get(PrimaryMID.pk == mid.pk) for mid in primary_mids
    ]

    expected = [
        {
            "pk": mid.pk,
            "payment_scheme.code": await payment_scheme_code(mid),
            "mid": mid.mid,
            "visa_bin": mid.visa_bin,
            "payment_enrolment_status": mid.payment_enrolment_status,
            "date_added": mid.date_added,
            "txm_status": mid.txm_status,
        }
        for mid in primary_mids
    ]
    actual = await list_primary_mids(plan_ref=merchant.plan, merchant_ref=merchant.pk)

    assert expected == actual
