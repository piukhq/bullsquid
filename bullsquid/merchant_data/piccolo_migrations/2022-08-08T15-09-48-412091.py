from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text

ID = "2022-08-08T15:09:48:412091"
VERSION = "0.74.4"
DESCRIPTION = "make location.location_id unique"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="Location",
        tablename="location",
        column_name="location_id",
        params={"unique": True},
        old_params={"unique": False},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
