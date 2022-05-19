"""Plan table definitions."""
from piccolo.columns import UUID, Boolean, Integer, Text
from piccolo.table import Table

from bullsquid.merchant_data.enums import PlanStatus


class Plan(Table):
    """Represents a loyalty plan that may contain any number of merchants."""

    pk = UUID(primary_key=True)
    name = Text(required=True, unique=True)
    status = Text(choices=PlanStatus, default=PlanStatus.ACTIVE)
    icon_url = Text(null=True, default=None)
    slug = Text(null=True, default=None, unique=True)
    plan_id = Integer(null=True, default=None, unique=True)
    is_deleted = Boolean(default=False)
