"""Plan table definitions."""
from piccolo.columns import Integer, Text

from bullsquid.merchant_data.tables import SoftDeletable, TableWithPK


class Plan(SoftDeletable, TableWithPK):
    """Represents a loyalty plan that may contain any number of merchants."""

    name = Text(required=True, unique=True)
    icon_url = Text(null=True, default=None)
    slug = Text(null=True, default=None, unique=True)
    plan_id = Integer(null=True, default=None, unique=True)

    @property
    def display_text(self) -> str:
        return self.name
