"""
Pydantic models used for CSV file imports.
"""
from pydantic import validator

from bullsquid.merchant_data.models import BaseModel
from bullsquid.merchant_data.validators import (
    nullify_blank_strings,
    string_must_not_be_blank,
)


class LocationFileRecord(BaseModel):
    """
    Models a single line of locations (or "long") CSV file.
    """

    merchant_name: str | None
    parent_name: str | None
    name: str | None
    location_id: str
    merchant_internal_id: str
    is_physical: bool
    address_line_1: str | None
    address_line_2: str | None
    town_city: str | None
    county: str | None
    country: str | None
    postcode: str | None
    visa_mids: str
    amex_mids: str
    mastercard_mids: str
    visa_secondary_mids: str
    mastercard_secondary_mids: str

    _ = validator("location_id", "merchant_internal_id", allow_reuse=True)(
        string_must_not_be_blank
    )
    _ = validator(
        "merchant_name",
        "parent_name",
        "name",
        "address_line_1",
        "address_line_2",
        "town_city",
        "county",
        "country",
        "postcode",
        allow_reuse=True,
    )(nullify_blank_strings)


class MerchantsFileRecord(BaseModel):
    """
    Models a single line of a merchants details CSV file
    """

    name: str
    location_label: str = "stores"

    _ = validator("name", "location_label", allow_reuse=True)(string_must_not_be_blank)


class IdentifiersFileRecord(BaseModel):
    """
    Models a single line of mids and secondary mids CSV file
    """

    merchant_name: str
    location_id: str
    visa_mids: str
    amex_mids: str
    mastercard_mids: str
    visa_secondary_mids: str
    mastercard_secondary_mids: str

    _ = validator("merchant_name", "location_id", allow_reuse=True)(
        string_must_not_be_blank
    )
