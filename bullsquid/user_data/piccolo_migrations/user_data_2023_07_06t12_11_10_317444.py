from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text


ID = "2023-07-06T12:11:10:317444"
VERSION = "0.105.0"
DESCRIPTION = "Make user profile fields nullable"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="user_data", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="UserProfile",
        tablename="user_profile",
        column_name="name",
        db_column_name="name",
        params={"null": True},
        old_params={"null": False},
        column_class=Text,
        old_column_class=Text,
    )

    manager.alter_column(
        table_class_name="UserProfile",
        tablename="user_profile",
        column_name="nickname",
        db_column_name="nickname",
        params={"null": True},
        old_params={"null": False},
        column_class=Text,
        old_column_class=Text,
    )

    manager.alter_column(
        table_class_name="UserProfile",
        tablename="user_profile",
        column_name="email_address",
        db_column_name="email_address",
        params={"null": True},
        old_params={"null": False},
        column_class=Text,
        old_column_class=Text,
    )

    manager.alter_column(
        table_class_name="UserProfile",
        tablename="user_profile",
        column_name="picture",
        db_column_name="picture",
        params={"null": True},
        old_params={"null": False},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
