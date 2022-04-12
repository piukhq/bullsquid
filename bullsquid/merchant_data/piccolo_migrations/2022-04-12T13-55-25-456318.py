from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text

ID = "2022-04-12T13:55:25:456318"
VERSION = "0.71.1"
DESCRIPTION = "remove unique constraint on location_id"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="Location",
        tablename="location",
        column_name="location_id",
        params={"unique": False},
        old_params={"unique": True},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
