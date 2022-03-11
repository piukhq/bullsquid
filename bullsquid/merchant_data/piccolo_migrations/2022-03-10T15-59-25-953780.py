from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Array, Text
from piccolo.columns.indexes import IndexMethod

ID = "2022-03-10T15:59:25:953780"
VERSION = "0.69.5"
DESCRIPTION = "replace merchant-payment_scheme relationship with string array"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="mids", description=DESCRIPTION
    )

    manager.drop_table(
        class_name="MerchantToPaymentScheme",
        tablename="merchant_to_payment_scheme",
    )

    manager.add_column(
        table_class_name="Merchant",
        tablename="merchant",
        column_name="payment_schemes",
        db_column_name="payment_schemes",
        column_class_name="Array",
        column_class=Array,
        params={
            "base_column": Text(
                default="",
                null=False,
                primary_key=False,
                unique=False,
                index=False,
                index_method=IndexMethod.btree,
                choices=None,
                db_column_name=None,
                secret=False,
            ),
            "default": list,
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
