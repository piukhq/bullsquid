"""
API endpoints for importing data en masse from files.
"""
from datetime import datetime
from enum import Enum
from uuid import uuid4

from fastapi import APIRouter, Form, UploadFile, status
from loguru import logger
from pydantic import UUID4, ValidationError
from bullsquid.settings import settings

from bullsquid.api.errors import APIMultiError, DataError
from bullsquid.merchant_data.csv_upload.file_handling import csv_model_reader
from bullsquid.merchant_data.csv_upload.models import (
    IdentifiersFileRecord,
    LocationFileRecord,
    MerchantsFileRecord,
)
from bullsquid.merchant_data.tasks import ImportLocationFileRecord, queue
from bullsquid.merchant_data.tasks.import_identifiers import ImportIdentifiersFileRecord
from bullsquid.merchant_data.tasks.import_merchants import ImportMerchantsFileRecord
from bullsquid.service.azure_storage import AzureBlobStorageServiceInterface

router = APIRouter(prefix="/plans/csv_upload")


class FileType(Enum):
    """Supported file formats for importing data from."""

    LOCATIONS = "locations"
    MERCHANT_DETAILS = "merchant_details"
    IDENTIFIERS = "identifiers"


async def import_locations_file(
    file: UploadFile, *, plan_ref: UUID4, merchant_ref: UUID4 | None
) -> None:
    """
    Import a locations ("long") file.
    """
    reader = csv_model_reader(file.file, row_model=LocationFileRecord)
    for record in reader:
        await queue.push(
            ImportLocationFileRecord(
                plan_ref=plan_ref, merchant_ref=merchant_ref, record=record
            )
        )


async def import_merchants_file(file: UploadFile, *, plan_ref: UUID4) -> None:
    """
    Import a merchant details file.
    """
    reader = csv_model_reader(file.file, row_model=MerchantsFileRecord)
    for record in reader:
        await queue.push(ImportMerchantsFileRecord(plan_ref=plan_ref, record=record))


async def import_identifiers_file(
    file: UploadFile, *, plan_ref: UUID4, merchant_ref: UUID4 | None
) -> None:
    """
    Import an identifiers file.
    """
    reader = csv_model_reader(file.file, row_model=IdentifiersFileRecord)
    for record in reader:
        await queue.push(
            ImportIdentifiersFileRecord(
                plan_ref=plan_ref, merchant_ref=merchant_ref, record=record
            )
        )


def archive_file(file: UploadFile) -> None:
    """
    Archive the file to blob storage.
    """
    file_date = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    default_filename = f"{uuid4()}-{file_date}.csv"
    filename = file.filename or default_filename
    if dsn := settings.blob_storage.dsn:
        logger.info("Archiving file to blob storage", filename=filename)
        storage = AzureBlobStorageServiceInterface(dsn)
        storage.upload_blob(
            file.file,
            container=settings.blob_storage.archive_container,
            blob=filename,
        )
    else:
        logger.warning(
            "Blob storage not configured, skipping file archival",
            filename=filename,
        )


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def csv_upload_file(
    file: UploadFile,
    file_type: FileType = Form(),
    plan_ref: UUID4 = Form(),
    merchant_ref: UUID4 | None = Form(default=None),
) -> None:
    """Bulk import data from a file in one of three supported formats."""
    try:
        match file_type:
            case FileType.LOCATIONS:
                await import_locations_file(
                    file, plan_ref=plan_ref, merchant_ref=merchant_ref
                )
            case FileType.MERCHANT_DETAILS:
                await import_merchants_file(file, plan_ref=plan_ref)
            case FileType.IDENTIFIERS:
                await import_identifiers_file(
                    file, plan_ref=plan_ref, merchant_ref=merchant_ref
                )
    except ValidationError as ex:
        raise APIMultiError(
            [
                DataError(
                    loc=["body", "file", error._loc],  # type: ignore
                    resource_name="CSV upload",
                    reason=str(error.exc),  # type: ignore
                )
                for error in ex.raw_errors
            ]
        )
    except Exception as ex:
        raise DataError(
            loc=["body", "file"], resource_name="CSV upload", reason=str(ex)
        ) from ex
    else:
        archive_file(file)
