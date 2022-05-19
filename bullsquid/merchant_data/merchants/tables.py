"""Merchant table definitions."""
from piccolo.columns import UUID, Boolean, ForeignKey, Text
from piccolo.table import Table

from bullsquid.merchant_data.enums import PlanStatus
from bullsquid.merchant_data.plans.tables import Plan


class Merchant(Table):
    """Represents a merchant such as Iceland or Wasabi."""

    pk = UUID(primary_key=True)
    name = Text(required=True, unique=True)
    status = Text(choices=PlanStatus, default=PlanStatus.ACTIVE)
    icon_url = Text(null=True, default=None)
    location_label = Text(required=True)
    is_deleted = Boolean(default=False)
    plan = ForeignKey(Plan, required=True, null=False)
