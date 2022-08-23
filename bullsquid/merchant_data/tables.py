"""
Global tables that don't belong to any submodule, or reference tables from
multiple submodules.
"""
from piccolo.columns import UUID, ForeignKey
from piccolo.table import Table

from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID


class LocationSecondaryMIDAssociation(Table):
    """Represents an association between a secondary MID and a location."""

    pk = UUID(primary_key=True)
    location = ForeignKey(Location)
    secondary_mid = ForeignKey(SecondaryMID)
