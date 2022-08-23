from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete, OnUpdate
from piccolo.columns.column_types import UUID, ForeignKey
from piccolo.columns.defaults.uuid import UUID4
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


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


class SecondaryMID(Table, tablename="secondary_mid"):
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


ID = "2022-08-19T16:12:00:037790"
VERSION = "0.74.4"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.add_table(
        "LocationSecondaryMIDAssociation",
        tablename="location_secondary_mid_association",
    )

    manager.add_column(
        table_class_name="LocationSecondaryMIDAssociation",
        tablename="location_secondary_mid_association",
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
        table_class_name="LocationSecondaryMIDAssociation",
        tablename="location_secondary_mid_association",
        column_name="location",
        db_column_name="location",
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

    manager.add_column(
        table_class_name="LocationSecondaryMIDAssociation",
        tablename="location_secondary_mid_association",
        column_name="secondary_mid",
        db_column_name="secondary_mid",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": SecondaryMID,
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

    return manager
