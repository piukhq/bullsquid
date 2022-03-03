from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Integer, Text

ID = "2022-02-23T17:09:32:210841"
VERSION = "0.69.2"
DESCRIPTION = "allow null slug and plan_id on merchant"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="mids", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="Merchant",
        tablename="merchant",
        column_name="slug",
        params={"null": True},
        old_params={"null": False},
        column_class=Text,
        old_column_class=Text,
    )

    manager.alter_column(
        table_class_name="Merchant",
        tablename="merchant",
        column_name="plan_id",
        params={"null": True},
        old_params={"null": False},
        column_class=Integer,
        old_column_class=Integer,
    )

    return manager
