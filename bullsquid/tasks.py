"""Tasks to be performed off the main thread."""
import asyncio
from uuid import UUID

import sentry_sdk
from loguru import logger
from pydantic import BaseModel
from qbert import Queue

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.merchants.db import merchant_has_onboarded_resources
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.service.txm import txm
from bullsquid.settings import settings


class OnboardPrimaryMIDs(BaseModel):
    """Onboard MIDs into Harmonia."""

    mid_refs: list[UUID]


class OffboardPrimaryMIDs(BaseModel):
    """Offboard MIDs from Harmonia."""

    mid_refs: list[UUID]


class OffboardAndDeletePrimaryMIDs(BaseModel):
    """Offboard MIDs from Harmonia, then mark them as deleted."""

    mid_refs: list[UUID]


class OffboardAndDeleteMerchant(BaseModel):
    """Offboard merchant from Harmonia, then mark them as deleted"""

    merchant_ref: UUID


queue = Queue(
    [
        OnboardPrimaryMIDs,
        OffboardPrimaryMIDs,
        OffboardAndDeletePrimaryMIDs,
        OffboardAndDeleteMerchant,
    ]
)


async def delete_fully_offboarded_merchants(merchant_refs: list[UUID]) -> None:
    """Delete fully offboarded merchants"""
    for merchant_ref in merchant_refs:
        if not await merchant_has_onboarded_resources(merchant_ref):
            await Merchant.update({Merchant.status: ResourceStatus.DELETED}).where(
                Merchant.pk == merchant_ref,
                Merchant.status == ResourceStatus.PENDING_DELETION,
            )


async def _run_job(message: BaseModel) -> None:
    match message:
        case OnboardPrimaryMIDs():
            await txm.onboard_mids(message.mid_refs)
            await PrimaryMID.update({PrimaryMID.txm_status: TXMStatus.ONBOARDED}).where(
                PrimaryMID.pk.is_in(message.mid_refs)
            )

        case OffboardPrimaryMIDs():
            await txm.offboard_mids(message.mid_refs)
            await PrimaryMID.update(
                {PrimaryMID.txm_status: TXMStatus.OFFBOARDED}
            ).where(PrimaryMID.pk.is_in(message.mid_refs))

        case OffboardAndDeletePrimaryMIDs():
            await txm.offboard_mids(message.mid_refs)
            await PrimaryMID.update(
                {
                    PrimaryMID.txm_status: TXMStatus.OFFBOARDED,
                    PrimaryMID.status: ResourceStatus.DELETED,
                    PrimaryMID.location: None,
                }
            ).where(PrimaryMID.pk.is_in(message.mid_refs))

            await delete_fully_offboarded_merchants(
                await PrimaryMID.select(PrimaryMID.merchant)
                .where(PrimaryMID.pk.is_in(message.mid_refs))
                .output(as_list=True)
            )

        case OffboardAndDeleteMerchant():
            onboarded_primary_mids = (
                await PrimaryMID.select(PrimaryMID.pk)
                .where(
                    PrimaryMID.merchant == message.merchant_ref,
                    PrimaryMID.txm_status == TXMStatus.ONBOARDED,
                )
                .output(as_list=True)
            )
            await queue.push(
                OffboardAndDeletePrimaryMIDs(mid_refs=onboarded_primary_mids)
            )
            # TODO: also offboard & delete secondary MIDs and identifiers


async def run_worker(*, burst: bool = False) -> None:
    """
    Run the task worker.
    Burst mode causes the worker to stop when the queue is empty.
    """
    logger.info("Bullsquid task worker starting up.")
    while True:
        for job in await queue.pull(settings.worker_concurrency):
            logger.debug(f"Running job: {job}")
            try:
                await _run_job(job.message)
            except Exception as ex:  # pylint: disable=broad-except
                # we catch all exceptions to prevent bad jobs from crashing the worker.

                if settings.debug:
                    logger.exception(ex)

                event_id = sentry_sdk.capture_exception()
                logger.warning(f"Job {job} failed: {ex} (event ID: {event_id})")

                await queue.fail_job(job.id)
            else:
                logger.debug(f"Job {job} succeeded")
                await queue.delete_job(job.id)

        if burst:
            return

        # reduce load on the database when the queue is empty.
        await asyncio.sleep(1)
