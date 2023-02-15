"""
Task functions for importing location records from CSV files.
"""
from uuid import UUID

from asyncpg import UniqueViolationError
from loguru import logger
from pydantic import BaseModel, ValidationError

from bullsquid.merchant_data.csv_upload.models import LocationFileRecord
from bullsquid.merchant_data.locations.models import LocationDetailMetadata
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID


class ImportLocationFileRecord(BaseModel):
    """
    Create a location from the given LocationFileRecord, also creating any dependent
    resources if necessary.
    """

    plan_ref: UUID
    merchant_ref: UUID | None
    record: LocationFileRecord


class LocationFileRecordError(Exception):
    """Base error type for all location file import errors."""


class SkipRecord(LocationFileRecordError):
    """Indicates that a record was intentionally skipped."""


class InvalidRecord(LocationFileRecordError):
    """The location file record is badly formed."""


class InvalidMerchant(LocationFileRecordError):
    """Merchant could not be found."""


class DuplicateLocation(LocationFileRecordError):
    """Location already exists."""


class DuplicatePrimaryMID(LocationFileRecordError):
    """MID already exists."""


class DuplicateSecondaryMID(LocationFileRecordError):
    """Secondary MID already exists."""


async def find_merchant(
    *, merchant_ref: UUID | None, merchant_name: str | None, plan_ref: UUID
) -> Merchant:
    """
    Look up a merchant in one of two ways:
    1. If `merchant_ref` is set, load the merchant with that primary key.
    2. If `merchant_name` is set, load a merchant with the same name (case insensitive).

    Raises InvalidRecord if both arguments are missing.
    Raises InvalidMerchant if no merchant can be found.
    Raises InvalidMerchant if a merchant is loaded by primary key
        but its name does not match `merchant_name`.
    """
    if merchant_ref:
        merchant = (
            await Merchant.objects()
            .where(Merchant.pk == merchant_ref, Merchant.plan == plan_ref)
            .first()
        )
    elif merchant_name:
        merchant = (
            await Merchant.objects()
            .where(
                Merchant.plan == plan_ref,
                Merchant.name.ilike(merchant_name.strip()),
            )
            .first()
        )
    else:
        raise InvalidRecord("Either merchant_ref or merchant_name must be given")

    if merchant is None:
        raise InvalidMerchant("No such merchant")

    # if uploading to a merchant, reject records with a non-null & different merchant name
    if (
        merchant_ref
        and merchant_name is not None
        and merchant.name.lower().strip() != merchant_name.lower().strip()
    ):
        raise SkipRecord("Merchant name does not match.")

    return merchant


async def import_location(
    record: LocationFileRecord, *, merchant: Merchant
) -> Location:
    """
    Import a location under the given merchant.
    """
    # use the same validation as a creation via the API.
    try:
        LocationDetailMetadata(
            name=record.name,
            location_id=record.name,
            merchant_internal_id=record.merchant_internal_id,
            is_physical_location=record.is_physical,
            address_line_1=record.address_line_1,
            address_line_2=record.address_line_2,
            town_city=record.town_city,
            county=record.county,
            country=record.country,
            postcode=record.postcode,
        )
    except ValidationError as ex:
        raise InvalidRecord(str(ex)) from ex

    # TODO: use locations.db.create_location when it is merged!!!!!!!!!!!!
    location = Location(
        location_id=record.location_id,
        name=record.name,
        is_physical_location=record.is_physical,
        address_line_1=record.address_line_1,
        address_line_2=record.address_line_2,
        town_city=record.town_city,
        county=record.county,
        country=record.country,
        postcode=record.postcode,
        merchant_internal_id=record.merchant_internal_id,
        merchant=merchant,
    )

    try:
        await location.save()
    except UniqueViolationError as ex:
        raise DuplicateLocation from ex
    return location


async def _any_mids_exist(
    *,
    visa_mids: list[str],
    amex_mids: list[str],
    mastercard_mids: list[str],
) -> bool:
    """
    Returns true if any of the given Visa, Amex, or Mastercard MIDs exist in the database.
    """

    # we could do this in a single query, but we'd need to be able to query with tuples in piccolo.
    # for example: .where(tuple_(PrimaryMID.mid, PrimaryMID.payment_scheme).is_in(...))
    # this doesn't seem to be possible yet, so we do three queries instead.
    async def exists(name: str, mids: list[str]) -> bool:
        if not mids:
            return False
        return await PrimaryMID.exists().where(
            PrimaryMID.payment_scheme == name, PrimaryMID.mid.is_in(mids)
        )

    return (
        await exists("visa", visa_mids)
        or await exists("amex", amex_mids)
        or await exists("mastercard", mastercard_mids)
    )


async def _any_secondary_mids_exist(
    *,
    visa_mids: list[str],
    mastercard_mids: list[str],
) -> bool:
    """
    Returns true if any of the given Visa or Mastercard secondary MIDs exist in the database.
    """

    async def exists(name: str, mids: list[str]) -> bool:
        if not mids:
            return False
        return await SecondaryMID.exists().where(
            SecondaryMID.payment_scheme == name, SecondaryMID.secondary_mid.is_in(mids)
        )

    return await exists("visa", visa_mids) or await exists(
        "mastercard", mastercard_mids
    )


async def import_primary_mids(
    *,
    visa_mids: list[str],
    amex_mids: list[str],
    mastercard_mids: list[str],
    merchant: Merchant,
    location: Location,
) -> None:
    """
    Import a set of Visa, Amex, and Mastercard MIDs and link them to the given location.
    Raises DuplicatePrimaryMID if any of the MIDs already exist.
    """
    if await _any_mids_exist(
        visa_mids=visa_mids, amex_mids=amex_mids, mastercard_mids=mastercard_mids
    ):
        raise DuplicatePrimaryMID

    for mid in visa_mids:
        primary_mid = PrimaryMID(
            mid=mid, payment_scheme="visa", merchant=merchant, location=location
        )
        await primary_mid.save()

    for mid in amex_mids:
        primary_mid = PrimaryMID(
            mid=mid, payment_scheme="amex", merchant=merchant, location=location
        )
        await primary_mid.save()

    for mid in mastercard_mids:
        primary_mid = PrimaryMID(
            mid=mid, payment_scheme="mastercard", merchant=merchant, location=location
        )
        await primary_mid.save()


async def import_secondary_mids(
    visa_mids: list[str],
    mastercard_mids: list[str],
    merchant: Merchant,
    location: Location,
) -> None:
    """
    Import a set of Visa and Mastercard secondary MIDs and link them to the given location.
    Raises DuplicateSecondaryMID if any of the secondary MIDs already exist.
    """
    if await _any_secondary_mids_exist(
        visa_mids=visa_mids, mastercard_mids=mastercard_mids
    ):
        raise DuplicateSecondaryMID

    for mid in visa_mids:
        secondary_mid = SecondaryMID(
            secondary_mid=mid,
            payment_scheme="visa",
            merchant=merchant,
        )
        await secondary_mid.save()
        await secondary_mid.add_m2m(location, m2m=SecondaryMID.locations)

    for mid in mastercard_mids:
        secondary_mid = SecondaryMID(
            secondary_mid=mid,
            payment_scheme="mastercard",
            merchant=merchant,
        )
        await secondary_mid.save()
        await secondary_mid.add_m2m(location, m2m=SecondaryMID.locations)


async def import_location_file_record(
    record: LocationFileRecord, *, plan_ref: UUID, merchant_ref: UUID | None
) -> None:
    """
    Import a location file record under a plan.
    If `merchant_ref` is passed, only records for that specific merchant will be loaded.
    """
    try:
        merchant = await find_merchant(
            merchant_ref=merchant_ref,
            merchant_name=record.merchant_name,
            plan_ref=plan_ref,
        )

        location = await import_location(record, merchant=merchant)

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
    except LocationFileRecordError as ex:
        logger.error(f"location file import raised error: {ex!r}")
        logger.warning("this should be sent to the action log")
