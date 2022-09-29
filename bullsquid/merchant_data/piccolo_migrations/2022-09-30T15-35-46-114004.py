from enum import Enum

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete, OnUpdate
from piccolo.columns.column_types import (
    UUID,
    Array,
    Boolean,
    ForeignKey,
    Text,
    Timestamptz,
)
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.defaults.uuid import UUID4
from piccolo.columns.indexes import IndexMethod

ID = "2022-09-30T15:35:46:114004"
VERSION = "0.74.4"
DESCRIPTION = "add comment table"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.add_table("Comment", tablename="comment")

    manager.add_column(
        table_class_name="Comment",
        tablename="comment",
        column_name="pk",
        db_column_name="pk",
        column_class_name="UUID",
        column_class=UUID,
        params={
            "default": UUID4(),
            "null": False,
            "primary_key": True,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="Comment",
        tablename="comment",
        column_name="text",
        db_column_name="text",
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

    manager.add_column(
        table_class_name="Comment",
        tablename="comment",
        column_name="owner",
        db_column_name="owner",
        column_class_name="UUID",
        column_class=UUID,
        params={
            "default": UUID4(),
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
        table_class_name="Comment",
        tablename="comment",
        column_name="owner_type",
        db_column_name="owner_type",
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
                "ResourceType",
                {
                    "PLAN": "plan",
                    "MERCHANT": "merchant",
                    "LOCATION": "location",
                    "PRIMARY_MID": "mid",
                    "SECONDARY_MID": "secondary_mid",
                    "PSIMI": "psimi",
                },
            ),
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="Comment",
        tablename="comment",
        column_name="subjects",
        db_column_name="subjects",
        column_class_name="Array",
        column_class=Array,
        params={
            "base_column": UUID(
                default=UUID4(),
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

    manager.add_column(
        table_class_name="Comment",
        tablename="comment",
        column_name="subject_type",
        db_column_name="subject_type",
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
                "ResourceType",
                {
                    "PLAN": "plan",
                    "MERCHANT": "merchant",
                    "LOCATION": "location",
                    "PRIMARY_MID": "mid",
                    "SECONDARY_MID": "secondary_mid",
                    "PSIMI": "psimi",
                },
            ),
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="Comment",
        tablename="comment",
        column_name="parent",
        db_column_name="parent",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": "self",
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
            "null": True,
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
        table_class_name="Comment",
        tablename="comment",
        column_name="is_edited",
        db_column_name="is_edited",
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
        table_class_name="Comment",
        tablename="comment",
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
        table_class_name="Comment",
        tablename="comment",
        column_name="created_at",
        db_column_name="created_at",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
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
        table_class_name="Comment",
        tablename="comment",
        column_name="created_by",
        db_column_name="created_by",
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
