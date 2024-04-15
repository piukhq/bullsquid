"""Useful functions to do with naming things."""

from typing import Type

from inflection import titleize, underscore
from piccolo.table import Table

from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.psimis.tables import PSIMI
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)


def get_pretty_table_name(table: Type[Table]) -> str:
    """
    Returns the prettified name of the given table.

    Examples:

        >>> get_pretty_table_name(PrimaryMID)
        'Primary MID'

        >>> get_pretty_table_name(PaymentScheme)
        'Payment Scheme'

        >>> get_pretty_table_name(PSIMI)
        'PSIMI'
    """
    if table == PSIMI:
        return "PSIMI"
    return titleize(table.__name__).replace("Mid", "MID")


def get_ref_name(table: Type[Table], *, plural: bool = False) -> str:
    """
    Returns the name of the field used to reference the given table in the API.

    ``Plural`` adds an "s" on the end.

    Examples:

        >>> get_ref_name(PrimaryMID)
        'mid_ref'

        >>> get_ref_name(PaymentScheme)
        'payment_scheme_slug'

        >>> get_ref_name(SecondaryMID, plural=True)
        'secondary_mid_refs'
    """
    match table.__qualname__:
        case PrimaryMID.__qualname__:
            name = "mid_ref"
        case PaymentScheme.__qualname__:
            name = "payment_scheme_slug"
        case SecondaryMIDLocationLink.__qualname__:
            name = "link_ref"
        case _:
            name = f"{underscore(table.__name__)}_ref"

    if plural:
        name = f"{name}s"

    return name
