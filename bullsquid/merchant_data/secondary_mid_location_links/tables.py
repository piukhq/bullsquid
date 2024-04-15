"""
The link between a secondary MID and a location.
"""

from piccolo.columns import UUID, ForeignKey
from piccolo.table import Table

from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID


class SecondaryMIDLocationLink(Table):
    """Represents an association between a secondary MID and a location."""

    pk = UUID(primary_key=True)
    secondary_mid = ForeignKey(SecondaryMID)
    location = ForeignKey(Location)
