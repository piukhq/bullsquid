"""
Task functions for importing mid records from CSV files.
"""
from uuid import UUID

from loguru import logger
from pydantic import BaseModel

from bullsquid.merchant_data.csv_upload.models import IdentifiersFileRecord
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.tasks.errors import SkipRecord
from bullsquid.merchant_data.tasks.import_locations import (
    find_merchant,
    import_primary_mids,
    import_secondary_mids,
)


class IdentifiersFileRecordError(Exception):
    """Base error type for all identifiers file import errors."""


class InvalidLocation(IdentifiersFileRecordError):
    """Location could not be found."""


class ImportIdentifiersFileRecord(BaseModel):
    """Create a set of identifiers from the given LocationFileRecord."""

    plan_ref: UUID
    merchant_ref: UUID | None
    record: IdentifiersFileRecord


async def import_identifiers_file_record(
    record: IdentifiersFileRecord, *, plan_ref: UUID, merchant_ref: UUID | None
) -> None:
    """
    Import a set of identifiers under the given merchant.
    """
    try:
        merchant = await find_merchant(
            merchant_ref=merchant_ref,
            merchant_name=record.merchant_name,
            plan_ref=plan_ref,
        )

        location = (
            await Location.objects()
            .where(
                Location.location_id == record.location_id,
                Location.merchant == merchant,
            )
            .first()
        )
        if location is None:
            raise InvalidLocation("No such location")

        await import_primary_mids(
            visa_mids=record.visa_mids.strip().split(),
            amex_mids=record.amex_mids.strip().split(),
            mastercard_mids=record.mastercard_mids.strip().split(),
            merchant=merchant,
            location=location,
        )

        await import_secondary_mids(
            visa_mids=record.visa_secondary_mids.strip().split(),
            mastercard_mids=record.mastercard_secondary_mids.strip().split(),
            merchant=merchant,
            location=location,
        )
    except SkipRecord:
        logger.warning(
            "record was intentionally skipped, this should be sent to the action log"
        )
    except IdentifiersFileRecordError as ex:
        logger.error(f"identifiers file import raised error: {ex!r}")
        logger.warning("this should be sent to the action log")
