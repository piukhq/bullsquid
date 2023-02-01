from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text

ID = "2023-02-01T12:13:08:268777"
VERSION = "0.97.0"
DESCRIPTION = "make psimi.payment_scheme_merchant_name nullable"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="PSIMI",
        tablename="psimi",
        column_name="payment_scheme_merchant_name",
        db_column_name="payment_scheme_merchant_name",
        params={"null": True},
        old_params={"null": False},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
