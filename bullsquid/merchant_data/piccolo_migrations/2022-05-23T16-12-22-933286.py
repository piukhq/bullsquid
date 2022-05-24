from enum import Enum

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text
from piccolo.columns.indexes import IndexMethod

ID = "2022-05-23T16:12:22:933286"
VERSION = "0.71.1"
DESCRIPTION = "remove is_deleted fields and change PlanStatus to ResourceStatus."


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.drop_column(
        table_class_name="Merchant",
        tablename="merchant",
        column_name="is_deleted",
        db_column_name="is_deleted",
    )

    manager.drop_column(
        table_class_name="Plan",
        tablename="plan",
        column_name="is_deleted",
        db_column_name="is_deleted",
    )

    manager.drop_column(
        table_class_name="PrimaryMID",
        tablename="primary_mid",
        column_name="is_deleted",
        db_column_name="is_deleted",
    )

    manager.add_column(
        table_class_name="PrimaryMID",
        tablename="primary_mid",
        column_name="status",
        db_column_name="status",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "active",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": True,
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

    manager.alter_column(
        table_class_name="Merchant",
        tablename="merchant",
        column_name="status",
        params={
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
            )
        },
        old_params={
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
            )
        },
        column_class=Text,
        old_column_class=Text,
    )

    manager.alter_column(
        table_class_name="Plan",
        tablename="plan",
        column_name="status",
        params={
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
            )
        },
        old_params={
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
            )
        },
        column_class=Text,
        old_column_class=Text,
    )

    return manager
