"""Plan table definitions."""
from piccolo.columns import UUID, Integer, Text
from piccolo.table import Table

from bullsquid.merchant_data.enums import ResourceStatus


class Plan(Table):
    """Represents a loyalty plan that may contain any number of merchants."""

    pk = UUID(primary_key=True)
    name = Text(required=True, unique=True)
    icon_url = Text(null=True, default=None)
    slug = Text(null=True, default=None, unique=True)
    plan_id = Integer(null=True, default=None, unique=True)
    status = Text(choices=ResourceStatus, default=ResourceStatus.ACTIVE)
