"""Merchant table definitions."""
from piccolo.columns import UUID, ForeignKey, Text
from piccolo.table import Table

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.plans.tables import Plan


class Merchant(Table):
    """Represents a merchant such as Iceland or Wasabi."""

    pk = UUID(primary_key=True)
    name = Text(required=True, unique=True)
    icon_url = Text(null=True, default=None)
    location_label = Text(required=True)
    status = Text(choices=ResourceStatus, default=ResourceStatus.ACTIVE)
    plan = ForeignKey(Plan, required=True, null=False)
