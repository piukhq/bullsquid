from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.table import Table

ID = "2023-01-20T11:34:19:160907"
VERSION = "0.97.0"
DESCRIPTION = "set secondary mid uniqueness to mid + payment scheme"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    async def modify_unique_constraint():
        await Table.raw(
            "ALTER TABLE secondary_mid DROP CONSTRAINT secondary_mid_secondary_mid_key"
        )
        await Table.raw(
            "CREATE UNIQUE INDEX unique_secondary_mid_payment_scheme "
            "ON secondary_mid(secondary_mid, payment_scheme)"
        )

    manager.add_raw(modify_unique_constraint)

    return manager
