from enum import Enum

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete, OnUpdate
from piccolo.columns.column_types import UUID, ForeignKey, Text, Timestamptz
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.defaults.uuid import UUID4
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class Merchant(Table, tablename="merchant"):
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


class PaymentScheme(Table, tablename="payment_scheme"):
    slug = Text(
        default="",
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name=None,
        secret=False,
    )


ID = "2022-05-31T17:50:27:717066"
VERSION = "0.74.4"
DESCRIPTION = "add secondary mid table"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.add_table("SecondaryMID", tablename="secondary_mid")

    manager.add_column(
        table_class_name="SecondaryMID",
        tablename="secondary_mid",
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
        table_class_name="SecondaryMID",
        tablename="secondary_mid",
        column_name="secondary_mid",
        db_column_name="secondary_mid",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
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
        table_class_name="SecondaryMID",
        tablename="secondary_mid",
        column_name="store_name",
        db_column_name="store_name",
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

    manager.add_column(
        table_class_name="SecondaryMID",
        tablename="secondary_mid",
        column_name="payment_scheme",
        db_column_name="payment_scheme",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": PaymentScheme,
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
        table_class_name="SecondaryMID",
        tablename="secondary_mid",
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
        table_class_name="SecondaryMID",
        tablename="secondary_mid",
        column_name="payment_enrolment_status",
        db_column_name="payment_enrolment_status",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "unknown",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": Enum(
                "PaymentEnrolmentStatus",
                {
                    "UNKNOWN": "unknown",
                    "ENROLLING": "enrolling",
                    "ENROLLED": "enrolled",
                    "REMOVED": "removed",
                },
            ),
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="SecondaryMID",
        tablename="secondary_mid",
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

    manager.add_column(
        table_class_name="SecondaryMID",
        tablename="secondary_mid",
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

    manager.add_column(
        table_class_name="SecondaryMID",
        tablename="secondary_mid",
        column_name="merchant",
        db_column_name="merchant",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": Merchant,
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
        column_name="merchant",
        params={"null": True},
        old_params={"null": False},
        column_class=ForeignKey,
        old_column_class=ForeignKey,
    )

    manager.alter_column(
        table_class_name="MerchantIdentifier",
        tablename="merchant_identifier",
        column_name="merchant",
        params={"null": True},
        old_params={"null": False},
        column_class=ForeignKey,
        old_column_class=ForeignKey,
    )

    manager.alter_column(
        table_class_name="PrimaryMID",
        tablename="primary_mid",
        column_name="payment_scheme",
        params={"null": True},
        old_params={"null": False},
        column_class=ForeignKey,
        old_column_class=ForeignKey,
    )

    manager.alter_column(
        table_class_name="PrimaryMID",
        tablename="primary_mid",
        column_name="merchant",
        params={"null": True},
        old_params={"null": False},
        column_class=ForeignKey,
        old_column_class=ForeignKey,
    )

    return manager
