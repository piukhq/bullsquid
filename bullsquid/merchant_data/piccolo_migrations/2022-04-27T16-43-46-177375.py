from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text

ID = "2022-04-27T16:43:46:177375"
VERSION = "0.71.1"
DESCRIPTION = "set plan.status default to active"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="Plan",
        tablename="plan",
        column_name="status",
        params={"default": "active"},
        old_params={"default": ""},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
