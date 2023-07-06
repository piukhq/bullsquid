from piccolo.table import Table

from piccolo.columns import Text, Timestamptz


class UserProfile(Table):
    """
    Represents an Auth0 user's profile information.
    """

    user_id = Text(primary_key=True)
    name = Text(null=True)
    nickname = Text(null=True)
    email_address = Text(null=True)
    picture = Text(null=True)
    created_at = Timestamptz()
    updated_at = Timestamptz()
