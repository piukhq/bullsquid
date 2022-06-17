from piccolo.apps.migrations.auto.migration_manager import MigrationManager

ID = "2022-06-17T17:52:01:312550"
VERSION = "0.74.4"
DESCRIPTION = "rename store_name to payment_scheme_store_name on secondary MID table"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.rename_column(
        table_class_name="SecondaryMID",
        tablename="secondary_mid",
        old_column_name="store_name",
        new_column_name="payment_scheme_store_name",
        old_db_column_name="store_name",
        new_db_column_name="payment_scheme_store_name",
    )

    return manager
