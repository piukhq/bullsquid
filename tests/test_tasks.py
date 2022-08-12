"""Tests for the task worker."""

from unittest.mock import patch

from qbert.enums import JobStatus
from qbert.tables import Job
from ward import raises, test

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.tasks import (
    OffboardAndDeletePrimaryMIDs,
    OffboardPrimaryMIDs,
    OnboardPrimaryMIDs,
    queue,
    run_worker,
)
from tests.fixtures import database
from tests.merchant_data.factories import primary_mid_factory


@test("run_worker executes jobs")
async def _(_: None = database) -> None:
    primary_mid = await primary_mid_factory()
    await queue.push(OnboardPrimaryMIDs(mid_refs=[primary_mid.pk]))
    assert await Job.count().where(Job.message_type == OnboardPrimaryMIDs.__name__) == 1

    with patch("bullsquid.tasks.logger"):
        await run_worker(burst=True)

    assert await Job.count().where(Job.message_type == OnboardPrimaryMIDs.__name__) == 0


@test("run_worker handles exceptions without crashing")
async def _(_: None = database) -> None:
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

    with (
        patch("bullsquid.tasks.logger"),
        patch("bullsquid.tasks.txm.onboard_mids", side_effect=Exception),
    ):
        await run_worker(burst=True)

    assert (
        await Job.count().where(
            Job.message_type == OnboardPrimaryMIDs.__name__,
            Job.status.is_in([JobStatus.QUEUED, JobStatus.FAILED]),
            Job.failed_attempts == 1,
        )
        == 1
    )


@test("run_worker sleeps when the queue is empty")
async def _(_: None = database) -> None:
    primary_mid = await primary_mid_factory()
    await queue.push(OnboardPrimaryMIDs(mid_refs=[primary_mid.pk]))

    class MockedSleep(Exception):
        """
        Causes asyncio.sleep to raise an exception, conveniently allowing us to
        both test that it is called and break out of the loop.
        """

    with (
        patch("bullsquid.tasks.logger"),
        patch("bullsquid.tasks.asyncio.sleep", side_effect=MockedSleep),
        raises(MockedSleep),
    ):
        await run_worker()


@test("the task worker can onboard primary MIDs")
async def _(_: None = database) -> None:
    primary_mid = await primary_mid_factory(txm_status=TXMStatus.NOT_ONBOARDED)

    await queue.push(OnboardPrimaryMIDs(mid_refs=[primary_mid.pk]))
    with patch("bullsquid.tasks.logger"):
        await run_worker(burst=True)

    primary_mid = await PrimaryMID.objects().get(PrimaryMID.pk == primary_mid.pk)
    assert primary_mid.txm_status == TXMStatus.ONBOARDED
    assert primary_mid.status == ResourceStatus.ACTIVE


@test("the task worker can offboard primary MIDs")
async def _(_: None = database) -> None:
    primary_mid = await primary_mid_factory(txm_status=TXMStatus.ONBOARDED)

    await queue.push(OffboardPrimaryMIDs(mid_refs=[primary_mid.pk]))
    with patch("bullsquid.tasks.logger"):
        await run_worker(burst=True)

    primary_mid = await PrimaryMID.objects().get(PrimaryMID.pk == primary_mid.pk)
    assert primary_mid.txm_status == TXMStatus.OFFBOARDED
    assert primary_mid.status == ResourceStatus.ACTIVE


@test("the task worker can offboard and delete primary MIDs")
async def _(_: None = database) -> None:
    primary_mid = await primary_mid_factory(txm_status=TXMStatus.ONBOARDED)

    await queue.push(OffboardAndDeletePrimaryMIDs(mid_refs=[primary_mid.pk]))
    with patch("bullsquid.tasks.logger"):
        await run_worker(burst=True)

    primary_mid = await PrimaryMID.objects().get(PrimaryMID.pk == primary_mid.pk)
    assert primary_mid.txm_status == TXMStatus.OFFBOARDED
    assert primary_mid.status == ResourceStatus.DELETED
