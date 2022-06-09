from enum import Enum

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text
from piccolo.columns.indexes import IndexMethod

ID = "2022-06-09T10:30:53:301584"
VERSION = "0.74.4"
DESCRIPTION = "replace identifier.is_deleted with identifier.status"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.drop_column(
        table_class_name="Identifier",
        tablename="identifier",
        column_name="is_deleted",
        db_column_name="is_deleted",
    )

    manager.add_column(
        table_class_name="Identifier",
        tablename="identifier",
        column_name="status",
        db_column_name="status",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "active",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": Enum(
                "ResourceStatus",
                {
                    "ACTIVE": "active",
                    "DRAFT": "draft",
                    "COMING_SOON": "coming_soon",
                    "SUSPENDED": "suspended",
                    "PENDING_DELETION": "pending_deletion",
                    "DELETED": "deleted",
                },
            ),
            "db_column_name": None,
            "secret": False,
        },
    )

    return manager
