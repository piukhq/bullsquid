"""Action log table definitions."""
from enum import Enum

from piccolo.columns import JSON, UUID, Timestamptz

from bullsquid.merchant_data.enums import ResourceType
from bullsquid.merchant_data.tables import TableWithPK


class ActionList(Enum):
    """List of actions that a user can make"""

    CREATE = 1
    UPDATE = 2
    DELETE = 3


class Action(TableWithPK):
    """Represents a logged action made by a user"""

    date = Timestamptz()
    user = UUID(required=True)
    action = ActionList(required=True)
    entity = UUID(required=True)
    entity_type = ResourceType(required=True)
    changes = JSON(default=str, required=True)
