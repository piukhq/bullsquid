from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Integer, Text
from piccolo.columns.indexes import IndexMethod

ID = "2022-05-11T16:53:42:122451"
VERSION = "0.71.1"
DESCRIPTION = "add code and label fields to payment scheme"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="PaymentScheme",
        tablename="payment_scheme",
        column_name="code",
        db_column_name="code",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "default": 0,
            "null": False,
            "primary_key": False,
            "unique": True,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="PaymentScheme",
        tablename="payment_scheme",
        column_name="label",
        db_column_name="label",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    return manager
