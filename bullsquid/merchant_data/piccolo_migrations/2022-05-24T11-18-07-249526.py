from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Integer

ID = "2022-05-24T11:18:07:249526"
VERSION = "0.71.1"
DESCRIPTION = "make payment scheme code unique"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="PaymentScheme",
        tablename="payment_scheme",
        column_name="code",
        params={"unique": True},
        old_params={"unique": False},
        column_class=Integer,
        old_column_class=Integer,
    )

    return manager
