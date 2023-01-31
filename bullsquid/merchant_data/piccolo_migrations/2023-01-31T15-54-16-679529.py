from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text

ID = "2023-01-31T15:54:16:679529"
VERSION = "0.97.0"
DESCRIPTION = "rename identifier to psimi"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.rename_table(
        old_class_name="Identifier",
        old_tablename="identifier",
        new_class_name="PSIMI",
        new_tablename="psimi",
    )

    return manager
