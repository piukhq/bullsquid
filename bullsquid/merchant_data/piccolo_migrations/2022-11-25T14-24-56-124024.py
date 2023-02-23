from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.table import Table

ID = "2022-11-25T14:24:56:124024"
VERSION = "0.74.4"
DESCRIPTION = "set primary mid uniqueness to mid + payment scheme"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    async def modify_unique_constraint():
        await Table.raw("ALTER TABLE primary_mid DROP CONSTRAINT mid_mid_key")
        await Table.raw(
            "CREATE UNIQUE INDEX unique_mid_payment_scheme "
            "ON primary_mid(mid, payment_scheme)"
        )

    manager.add_raw(modify_unique_constraint)

    return manager
