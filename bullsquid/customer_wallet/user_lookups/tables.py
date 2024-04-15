"""Table definitions for the customer wallet API."""

from piccolo.columns import JSON, Serial, Text, Timestamptz
from piccolo.table import Table


class UserLookup(Table):
    """Stores user lookups, uniquely identified by user_id."""

    # piccolo would create this for us automatically, but it's added dynamically
    # and pylint complains that `.id` doesn't exist.
    id = Serial(index=False, primary_key=True, db_column_name="id")
    auth_id = Text(index=True)
    user_id = Text()
    channel = Text()
    display_text = Text()
    lookup_type = Text()
    criteria = JSON()
    updated_at = Timestamptz()
