from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text

ID = "2022-11-03T14:40:00:713502"
VERSION = "0.74.4"
DESCRIPTION = "drop payment scheme code and label columns"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.drop_column(
        table_class_name="PaymentScheme",
        tablename="payment_scheme",
        column_name="code",
        db_column_name="code",
    )

    manager.drop_column(
        table_class_name="PaymentScheme",
        tablename="payment_scheme",
        column_name="label",
        db_column_name="label",
    )

    manager.alter_column(
        table_class_name="PrimaryMID",
        tablename="primary_mid",
        column_name="status",
        params={"index": False},
        old_params={"index": True},
        column_class=Text,
        old_column_class=Text,
    )

    manager.alter_column(
        table_class_name="SecondaryMID",
        tablename="secondary_mid",
        column_name="status",
        params={"index": False},
        old_params={"index": True},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
