from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.table import Table


ID = "2023-04-21T12:17:24:504756"
VERSION = "0.105.0"
DESCRIPTION = "drop unique constraint on mid table"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    async def modify_unique_constraint():
        await Table.raw("DROP INDEX unique_mid_payment_scheme")

    manager.add_raw(modify_unique_constraint)

    return manager
