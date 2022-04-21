from enum import Enum

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Boolean, Text, Timestamptz
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.indexes import IndexMethod

ID = "2022-04-21T16:59:45:712466"
VERSION = "0.71.1"
DESCRIPTION = "combine mid data tables into one primary mid"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.drop_table(class_name="MIDMastercardData", tablename="mid_mastercard_data")

    manager.drop_table(class_name="MIDVisaData", tablename="mid_visa_data")

    manager.rename_table(
        old_class_name="MID",
        old_tablename="mid",
        new_class_name="PrimaryMID",
        new_tablename="primary_mid",
    )

    manager.drop_column(
        table_class_name="PrimaryMID",
        tablename="primary_mid",
        column_name="mastercard_data",
        db_column_name="mastercard_data",
    )

    manager.drop_column(
        table_class_name="PrimaryMID",
        tablename="primary_mid",
        column_name="visa_data",
        db_column_name="visa_data",
    )

    manager.add_column(
        table_class_name="PrimaryMID",
        tablename="primary_mid",
        column_name="date_added",
        db_column_name="date_added",
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
        table_class_name="PrimaryMID",
        tablename="primary_mid",
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
        table_class_name="PrimaryMID",
        tablename="primary_mid",
        column_name="visa_bin",
        db_column_name="visa_bin",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": None,
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
        table_class_name="PrimaryMID",
        tablename="primary_mid",
        column_name="mid",
        params={"default": "", "null": False},
        old_params={"default": None, "null": True},
        column_class=Text,
        old_column_class=Text,
    )

    manager.alter_column(
        table_class_name="PrimaryMID",
        tablename="primary_mid",
        column_name="payment_enrolment_status",
        params={
            "choices": Enum(
                "PaymentEnrolmentStatus",
                {
                    "UNKNOWN": "unknown",
                    "ENROLLING": "enrolling",
                    "ENROLLED": "enrolled",
                    "REMOVED": "removed",
                },
            )
        },
        old_params={
            "choices": Enum(
                "PaymentEnrolmentStatus",
                {
                    "UNKNOWN": "unknown",
                    "ENROLLING": "enrolling",
                    "ENROLLED": "enrolled",
                    "FAILED": "failed",
                },
            )
        },
        column_class=Text,
        old_column_class=Text,
    )

    return manager
