"""Tests for the task worker."""

from unittest.mock import patch

import pytest
from qbert.enums import JobStatus
from qbert.tables import Job

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.tasks import (
    OffboardAndDeleteMerchant,
    OffboardAndDeletePlan,
    OffboardAndDeletePrimaryMIDs,
    OffboardPrimaryMIDs,
    OnboardPrimaryMIDs,
    queue,
    run_worker,
)
from tests.helpers import Factory


async def test_run_worker_jobs(primary_mid_factory: Factory[PrimaryMID]) -> None:
    primary_mid = await primary_mid_factory()
    await queue.push(OnboardPrimaryMIDs(mid_refs=[primary_mid.pk]))
    assert await Job.count().where(Job.message_type == OnboardPrimaryMIDs.__name__) == 1

    await run_worker(burst=True)

    assert await Job.count().where(Job.message_type == OnboardPrimaryMIDs.__name__) == 0


async def test_run_worker_exceptions(primary_mid_factory: Factory[PrimaryMID]) -> None:
    primary_mid = await primary_mid_factory()
    await queue.push(OnboardPrimaryMIDs(mid_refs=[primary_mid.pk]))
    assert (
        await Job.count().where(
            Job.message_type == OnboardPrimaryMIDs.__name__,
            Job.status == JobStatus.QUEUED,
            Job.failed_attempts == 0,
        )
        == 1
    )

    with patch("bullsquid.merchant_data.tasks.txm.onboard_mids", side_effect=Exception):
        await run_worker(burst=True)

    assert (
        await Job.count().where(
            Job.message_type == OnboardPrimaryMIDs.__name__,
            Job.status.is_in([JobStatus.QUEUED, JobStatus.FAILED]),
            Job.failed_attempts == 1,
        )
        == 1
    )


async def test_run_worker_sleep(primary_mid_factory: Factory[PrimaryMID]) -> None:
    primary_mid = await primary_mid_factory()
    await queue.push(OnboardPrimaryMIDs(mid_refs=[primary_mid.pk]))

    class MockedSleep(Exception):
        """
        Causes asyncio.sleep to raise an exception, conveniently allowing us to
        both test that it is called and break out of the loop.
        """

    with (
        patch("bullsquid.merchant_data.tasks.asyncio.sleep", side_effect=MockedSleep),
        pytest.raises(MockedSleep),
    ):
        await run_worker()


async def test_onboard_primary_mids(primary_mid_factory: Factory[PrimaryMID]) -> None:
    primary_mid = await primary_mid_factory(txm_status=TXMStatus.NOT_ONBOARDED)

    await queue.push(OnboardPrimaryMIDs(mid_refs=[primary_mid.pk]))
    await run_worker(burst=True)

    expected = await PrimaryMID.objects().get(PrimaryMID.pk == primary_mid.pk)
    assert expected is not None
    assert expected.txm_status == TXMStatus.ONBOARDED
    assert expected.status == ResourceStatus.ACTIVE


async def test_offboard_primary_mids(primary_mid_factory: Factory[PrimaryMID]) -> None:
    primary_mid = await primary_mid_factory(txm_status=TXMStatus.ONBOARDED)

    await queue.push(OffboardPrimaryMIDs(mid_refs=[primary_mid.pk]))
    await run_worker(burst=True)

    expected = await PrimaryMID.objects().get(PrimaryMID.pk == primary_mid.pk)
    assert expected is not None
    assert expected.txm_status == TXMStatus.OFFBOARDED
    assert expected.status == ResourceStatus.ACTIVE


async def test_offboard_delete_primary_mids(
    primary_mid_factory: Factory[PrimaryMID],
) -> None:
    primary_mid = await primary_mid_factory(txm_status=TXMStatus.ONBOARDED)

    await queue.push(OffboardAndDeletePrimaryMIDs(mid_refs=[primary_mid.pk]))
    await run_worker(burst=True)

    expected = await PrimaryMID.all_objects().get(PrimaryMID.pk == primary_mid.pk)
    assert expected is not None
    assert expected.txm_status == TXMStatus.OFFBOARDED
    assert expected.status == ResourceStatus.DELETED


async def test_offboard_delete_primary_mid_null_link(
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    primary_mid_factory: Factory[PrimaryMID],
) -> None:
    merchant = await merchant_factory()
    location = await location_factory(merchant=merchant)
    primary_mid = await primary_mid_factory(
        merchant=merchant, location=location, txm_status=TXMStatus.ONBOARDED
    )

    await queue.push(OffboardAndDeletePrimaryMIDs(mid_refs=[primary_mid.pk]))
    await run_worker(burst=True)

    expected = await PrimaryMID.all_objects().get(PrimaryMID.pk == primary_mid.pk)
    assert expected is not None
    assert expected.location is None


async def test_offboard_delete_merchant(
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
) -> None:
    merchant = await merchant_factory(status=ResourceStatus.PENDING_DELETION)
    primary_mid = await primary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.ONBOARDED
    )

    await queue.push(OffboardAndDeleteMerchant(merchant_ref=merchant.pk))

    # run this twice; once for OffboardAndDeleteMerchant and once more for
    # OffboardAndDeletePrimaryMIDs.
    # TODO: fix burst mode
    await run_worker(burst=True)
    await run_worker(burst=True)

    expected_merchant = await Merchant.all_objects().get(Merchant.pk == merchant.pk)
    assert expected_merchant is not None

    expected = await PrimaryMID.all_objects().get(PrimaryMID.pk == primary_mid.pk)
    assert expected is not None

    assert expected.txm_status == TXMStatus.OFFBOARDED
    assert expected.status == ResourceStatus.DELETED
    assert expected_merchant.status == ResourceStatus.DELETED


async def test_offboard_delete_plan(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
) -> None:
    plan = await plan_factory(status=ResourceStatus.PENDING_DELETION)
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(
        merchant=merchant, txm_status=TXMStatus.ONBOARDED
    )

    await queue.push(OffboardAndDeletePlan(plan_ref=plan.pk))

    # run this three times
    # 1. OffboardAndDeletePlan
    # 2. OffboardAndDeleteMerchant
    # 3. OffboardAndDeletePrimaryMIDs
    # TODO: fix burst mode
    for _ in range(3):
        await run_worker(burst=True)

    expected_plan = await Plan.all_objects().get(Plan.pk == plan.pk)
    assert expected_plan is not None

    expected_merchant = await Merchant.all_objects().get(Merchant.pk == merchant.pk)
    assert expected_merchant is not None

    expected = await PrimaryMID.all_objects().get(PrimaryMID.pk == primary_mid.pk)
    assert expected is not None

    assert expected.txm_status == TXMStatus.OFFBOARDED
    assert expected.status == ResourceStatus.DELETED
    assert expected_merchant.status == ResourceStatus.DELETED
    assert expected_plan.status == ResourceStatus.DELETED
