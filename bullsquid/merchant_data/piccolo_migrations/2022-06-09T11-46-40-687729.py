from enum import Enum

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text
from piccolo.columns.indexes import IndexMethod

ID = "2022-06-09T11:46:40:687729"
VERSION = "0.74.4"
DESCRIPTION = "add txm_status to identifiers"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="Identifier",
        tablename="identifier",
        column_name="txm_status",
        db_column_name="txm_status",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "not_onboarded",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": Enum(
                "TXMStatus",
                {
                    "NOT_ONBOARDED": "not_onboarded",
                    "ONBOARDED": "onboarded",
                    "OFFBOARDED": "offboarded",
                },
            ),
            "db_column_name": None,
            "secret": False,
        },
    )

    return manager
