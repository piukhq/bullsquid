"""Location table definitions."""
from piccolo.columns import (
    M2M,
    Boolean,
    ForeignKey,
    LazyTableReference,
    Text,
    Timestamptz,
)

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.tables import TableWithPK


class Location(TableWithPK):
    """Represents a location that can have multiple MIDs."""

    location_id = Text(required=True, unique=True)
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

    secondary_mids = M2M(
        LazyTableReference("SecondaryMIDLocationLink", "merchant_data")
    )

    @property
    def display_text(self) -> str:
        fields = [self.name, self.address_line_1, self.town_city, self.postcode]
        return ", ".join(field for field in fields if field)
