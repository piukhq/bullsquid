from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text


ID = "2023-11-21T15:33:55:085718"
VERSION = "0.119.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="Location",
        tablename="location",
        column_name="location_id",
        db_column_name="location_id",
        params={"unique": False},
        old_params={"unique": True},
        column_class=Text,
        old_column_class=Text,
    )
    return manager
