from piccolo.table import Table

from piccolo.columns import Text, Timestamptz


class UserProfile(Table):
    """
    Represents an Auth0 user's profile information.
    """

    user_id = Text(primary_key=True)
    name = Text()
    nickname = Text()
    email_address = Text()
    created_at = Timestamptz()
    updated_at = Timestamptz()
    picture = Text()
