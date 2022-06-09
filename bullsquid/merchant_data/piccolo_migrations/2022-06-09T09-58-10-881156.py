from piccolo.apps.migrations.auto.migration_manager import MigrationManager

ID = "2022-06-09T09:58:10:881156"
VERSION = "0.74.4"
DESCRIPTION = "rename MerchantIdentifier to Identifier"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.rename_table(
        old_class_name="MerchantIdentifier",
        old_tablename="merchant_identifier",
        new_class_name="Identifier",
        new_tablename="identifier",
    )

    return manager
