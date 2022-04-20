from enum import Enum

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Boolean, Text
from piccolo.columns.indexes import IndexMethod

ID = "2022-04-20T17:32:05:355591"
VERSION = "0.71.1"
DESCRIPTION = "remove fields from merchant that now exist on plan"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.drop_column(
        table_class_name="Merchant",
        tablename="merchant",
        column_name="payment_schemes",
        db_column_name="payment_schemes",
    )

    manager.drop_column(
        table_class_name="Merchant",
        tablename="merchant",
        column_name="plan_id",
        db_column_name="plan_id",
    )

    manager.drop_column(
        table_class_name="Merchant",
        tablename="merchant",
        column_name="slug",
        db_column_name="slug",
    )

    manager.add_column(
        table_class_name="Merchant",
        tablename="merchant",
        column_name="is_deleted",
        db_column_name="is_deleted",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": False,
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

    manager.add_column(
        table_class_name="Merchant",
        tablename="merchant",
        column_name="status",
        db_column_name="status",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": Enum(
                "PlanStatus",
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
