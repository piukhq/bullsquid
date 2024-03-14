from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text
from piccolo.table import Table

ID = "2024-03-14T13:53:18:734009"
VERSION = "0.121.0"
DESCRIPTION = "make location ID required, and replace empty location IDs with UUIDs."


class Location(Table):
    pass


async def forwards() -> MigrationManager:
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    async def patch_empty_location_ids() -> None:
        await Location.raw(
            "UPDATE location SET location_id = uuid_generate_v4() WHERE location_id = ''"
        )

    manager.add_raw(patch_empty_location_ids)

    manager.alter_column(
        table_class_name="Location",
        tablename="location",
        column_name="location_id",
        db_column_name="location_id",
        params={"null": False},
        old_params={"null": True},
        column_class=Text,
        old_column_class=Text,
        schema=None,
    )

    return manager
