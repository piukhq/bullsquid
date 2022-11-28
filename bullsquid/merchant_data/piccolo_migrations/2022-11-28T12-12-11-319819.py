from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns import UUID
from piccolo.columns.base import OnDelete, OnUpdate
from piccolo.columns.column_types import ForeignKey
from piccolo.columns.defaults.uuid import UUID4
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table

ID = "2022-11-28T12:12:11:319819"
VERSION = "0.74.4"
DESCRIPTION = "add parent foreign key to location table"


class Location(Table, tablename="location"):
    pk = UUID(
        default=UUID4(),
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name=None,
        secret=False,
    )


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    # we have to add the foreign key without a "self" reference first,
    # and then alter it to be a "self" reference later.
    # otherwise the migration crashes saying it can't find an "id" column.
    # suspected piccolo bug.
    manager.add_column(
        table_class_name="Location",
        tablename="location",
        column_name="parent",
        db_column_name="parent",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": Location,
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

    manager.alter_column(
        table_class_name="Location",
        tablename="location",
        column_name="parent",
        db_column_name="parent",
        params={"references": "self"},
        old_params={"references": Location},
        column_class=ForeignKey,
        old_column_class=ForeignKey,
    )

    return manager
