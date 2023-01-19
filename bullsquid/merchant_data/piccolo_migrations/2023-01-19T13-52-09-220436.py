from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text

ID = "2023-01-19T13:52:09:220436"
VERSION = "0.97.0"
DESCRIPTION = "make location_id nullable for sub-locations"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="Location",
        tablename="location",
        column_name="location_id",
        db_column_name="location_id",
        params={"null": True},
        old_params={"null": False},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
