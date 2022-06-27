from piccolo.apps.migrations.auto.migration_manager import MigrationManager

ID = "2022-06-27T14:05:18:070026"
VERSION = "0.74.4"
DESCRIPTION = "rename identifier name to payment_scheme_merchant_name"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.rename_column(
        table_class_name="Identifier",
        tablename="identifier",
        old_column_name="name",
        new_column_name="payment_scheme_merchant_name",
        old_db_column_name="name",
        new_db_column_name="payment_scheme_merchant_name",
    )

    return manager
