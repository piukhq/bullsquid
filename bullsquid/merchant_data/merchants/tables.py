"""Merchant table definitions."""
from piccolo.columns import ForeignKey, Text

from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.tables import BaseTable


class Merchant(BaseTable):
    """Represents a merchant such as Iceland or Wasabi."""

    name = Text(required=True, unique=True)
    icon_url = Text(null=True, default=None)
    location_label = Text(required=True)
    plan = ForeignKey(Plan, required=True, null=False)

    @property
    def display_text(self) -> str:
        return self.name
