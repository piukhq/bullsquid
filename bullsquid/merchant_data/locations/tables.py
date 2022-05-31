"""Location table definitions."""
from piccolo.columns import UUID, Boolean, ForeignKey, Text, Timestamptz
from piccolo.table import Table

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.merchants.tables import Merchant


class Location(Table):
    """Represents a location that can have multiple MIDs."""

    pk = UUID(primary_key=True)
    location_id = Text(required=True)
    name = Text(required=True)
    is_physical_location = Boolean(default=True)
    address_line_1 = Text(null=True, default=None)
    address_line_2 = Text(null=True, default=None)
    town_city = Text(null=True, default=None)
    county = Text(null=True, default=None)
    country = Text(null=True, default=None)
    postcode = Text(null=True, default=None)
    merchant_internal_id = Text(null=True, default=None)
    date_added = Timestamptz()
    status = Text(choices=ResourceStatus, default=ResourceStatus.ACTIVE)
    merchant = ForeignKey(Merchant, required=True)
