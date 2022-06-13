"""Table definitions for the customer wallet API."""
from piccolo.columns import JSON, Text, Timestamptz
from piccolo.table import Table


class UserLookup(Table):
    """Stores user lookups, uniquely identified by user_id."""

    auth_id = Text(index=True)
    user_id = Text(unique=True)
    channel = Text()
    display_text = Text()
    lookup_type = Text()
    criteria = JSON()
    updated_at = Timestamptz()
