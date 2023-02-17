"""
Task functions for importing merchants records from CSV files.
"""
from uuid import UUID

from pydantic import BaseModel, ValidationError

from bullsquid.merchant_data.csv_upload.models import MerchantsFileRecord
from bullsquid.merchant_data.merchants import db
from bullsquid.merchant_data.merchants.models import CreateMerchantRequest


class ImportMerchantsFileRecord(BaseModel):
    """
    Create a location from the given MerchantsFileRecord, also creating any dependent
    resources if necessary.
    """

    plan_ref: UUID
    record: MerchantsFileRecord


class MerchantsFileRecordError(Exception):
    """Base error type for all merchant file import errors."""


class InvalidRecord(MerchantsFileRecordError):
    """The merchant file record is badly formed."""


async def import_merchant_file_record(
    record: MerchantsFileRecord, *, plan_ref: UUID
) -> None:
    """
    Import a merchant under the given merchant.
    """
    # use the same validation as a creation via the API.
    try:
        merchant_data = CreateMerchantRequest(
            name=record.name,
            icon_url=None,
            location_label=record.location_label,
        )
    except ValidationError as ex:
        raise InvalidRecord(str(ex)) from ex

    plan = await db.get_plan(plan_ref)
    await db.create_merchant(merchant_data.dict(), plan=plan)
