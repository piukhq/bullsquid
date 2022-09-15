"""Location table definitions."""
from piccolo.columns import (
    M2M,
    UUID,
    Boolean,
    ForeignKey,
    LazyTableReference,
    Text,
    Timestamptz,
)
from piccolo.table import Table

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.merchants.tables import Merchant


class Location(Table):
    """Represents a location that can have multiple MIDs."""

    pk = UUID(primary_key=True)
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
        LazyTableReference("LocationSecondaryMIDLink", "merchant_data")
    )

    @staticmethod
    def make_title(
        name: str,
        address_line_1: str | None,
        town_city: str | None,
        postcode: str | None,
    ) -> str:
        """Makes a location "title" from the given fields."""
        parts = [part for part in [name, address_line_1, town_city, postcode] if part]
        return ", ".join(parts)

    @property
    def title(self) -> str:
        """Calls Location.make_title with this location's fields."""
        return Location.make_title(
            self.name, self.address_line_1, self.town_city, self.postcode
        )
