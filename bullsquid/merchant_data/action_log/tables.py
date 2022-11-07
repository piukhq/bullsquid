"""Action log table definitions."""
from piccolo.columns import Text, Timestamptz

from bullsquid.merchant_data.tables import TableWithPK


class Action(TableWithPK):
    """Represents a logged action made by a user"""

    date = Timestamptz()
    user = Text(required=True)
    action = Text(required=True)
    entity_changed = Text(required=True)
    before_change = Text(required=True)
    after_change = Text(required=True)
