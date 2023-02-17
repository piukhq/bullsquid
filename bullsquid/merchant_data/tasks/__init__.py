"""Tasks to be performed off the main thread."""
import asyncio
from typing import cast
from uuid import UUID

import sentry_sdk
from loguru import logger
from pydantic import BaseModel
from qbert import Queue

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.merchants.db import merchant_has_onboarded_resources
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.db import plan_has_onboarded_resources
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.service.txm import txm
from bullsquid.merchant_data.tasks.import_identifiers import (
    ImportIdentifiersFileRecord,
    import_identifiers_file_record,
)
from bullsquid.merchant_data.tasks.import_locations import (
    ImportLocationFileRecord,
    import_location_file_record,
)
from bullsquid.merchant_data.tasks.import_merchants import (
    ImportMerchantsFileRecord,
    import_merchant_file_record,
)
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
    """Offboard all resources under a merchant, then mark it as deleted."""

    merchant_ref: UUID


class OffboardAndDeletePlan(BaseModel):
    """Offboard all resources under a plan and then mark it as deleted."""

    plan_ref: UUID


queue = Queue(
    [
        OnboardPrimaryMIDs,
        OffboardPrimaryMIDs,
        OffboardAndDeletePrimaryMIDs,
        OffboardAndDeleteMerchant,
        OffboardAndDeletePlan,
        ImportLocationFileRecord,
        ImportMerchantsFileRecord,
        ImportIdentifiersFileRecord,
    ]
)


async def delete_fully_offboarded_plan(plan_ref: UUID) -> None:
    """Delete the given plan if it is fully offboarded."""
    if not await plan_has_onboarded_resources(plan_ref):
        await Plan.update({Plan.status: ResourceStatus.DELETED}).where(
            Plan.pk == plan_ref,
            Plan.status == ResourceStatus.PENDING_DELETION,
        )


async def delete_fully_offboarded_merchants(merchant_refs: list[UUID]) -> None:
    """Delete the given merchants if they are fully offboarded."""
    for merchant_ref in merchant_refs:
        if not await merchant_has_onboarded_resources(merchant_ref):
            # we cast for mypy's benefit here, because we know that the merchant exists
            merchant = cast(
                Merchant, await Merchant.objects().get(Merchant.pk == merchant_ref)
            )

            if merchant.status != ResourceStatus.PENDING_DELETION:
                continue

            merchant.status = ResourceStatus.DELETED
            await merchant.save()

            await delete_fully_offboarded_plan(merchant.plan)


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
                await PrimaryMID.all_select(PrimaryMID.merchant)
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

            await PrimaryMID.update(
                {PrimaryMID.status: ResourceStatus.PENDING_DELETION}
            ).where(PrimaryMID.pk.is_in(onboarded_primary_mids))

            await queue.push(
                OffboardAndDeletePrimaryMIDs(mid_refs=onboarded_primary_mids)
            )
            # TODO: also offboard & delete secondary MIDs and PSIMIs

        case OffboardAndDeletePlan():
            merchants = await Merchant.objects().where(
                Merchant.plan == message.plan_ref
            )
            for merchant in merchants:
                merchant.status = ResourceStatus.PENDING_DELETION
                await merchant.save()
                await queue.push(OffboardAndDeleteMerchant(merchant_ref=merchant.pk))
        case ImportLocationFileRecord():
            await import_location_file_record(
                message.record,
                plan_ref=message.plan_ref,
                merchant_ref=message.merchant_ref,
            )
        case ImportMerchantsFileRecord():
            await import_merchant_file_record(message.record, plan_ref=message.plan_ref)
        case ImportIdentifiersFileRecord():
            await import_identifiers_file_record(
                message.record,
                plan_ref=message.plan_ref,
                merchant_ref=message.merchant_ref,
            )


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
                logger.warning(f"Job {job} failed: {ex!r} (event ID: {event_id})")

                await queue.fail_job(job.id)
            else:
                logger.debug(f"Job {job} succeeded")
                await queue.delete_job(job.id)

        if burst:
            return

        # reduce load on the database when the queue is empty.
        await asyncio.sleep(1)
