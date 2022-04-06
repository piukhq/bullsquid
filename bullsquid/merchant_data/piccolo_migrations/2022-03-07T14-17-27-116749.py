from enum import Enum

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete, OnUpdate
from piccolo.columns.column_types import (
    UUID,
    Boolean,
    ForeignKey,
    Integer,
    Serial,
    Text,
)
from piccolo.columns.defaults.uuid import UUID4
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class MIDMastercardData(Table, tablename="mid_mastercard_data"):
    id = Serial(
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name="id",
        secret=False,
    )


class MIDVisaData(Table, tablename="mid_visa_data"):
    id = Serial(
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name="id",
        secret=False,
    )


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


ID = "2022-03-07T14:17:27:116749"
VERSION = "0.69.5"
DESCRIPTION = "initial schema"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.add_table("MID", tablename="mid")

    manager.add_table("Location", tablename="location")

    manager.add_table("MIDVisaData", tablename="mid_visa_data")

    manager.add_table("PaymentScheme", tablename="payment_scheme")

    manager.add_table("MIDMastercardData", tablename="mid_mastercard_data")

    manager.add_table("Merchant", tablename="merchant")

    manager.add_table("MerchantToPaymentScheme", tablename="merchant_to_payment_scheme")

    manager.add_column(
        table_class_name="MID",
        tablename="mid",
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
        table_class_name="MID",
        tablename="mid",
        column_name="mid",
        db_column_name="mid",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": None,
            "null": True,
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
        table_class_name="MID",
        tablename="mid",
        column_name="payment_scheme",
        db_column_name="payment_scheme",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": PaymentScheme,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
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
        table_class_name="MID",
        tablename="mid",
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
                    "FAILED": "failed",
                },
            ),
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="MID",
        tablename="mid",
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
        table_class_name="MID",
        tablename="mid",
        column_name="mastercard_data",
        db_column_name="mastercard_data",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": MIDMastercardData,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
            "null": True,
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
        table_class_name="MID",
        tablename="mid",
        column_name="visa_data",
        db_column_name="visa_data",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": MIDVisaData,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
            "null": True,
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
        table_class_name="Location",
        tablename="location",
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
        table_class_name="Location",
        tablename="location",
        column_name="location_id",
        db_column_name="location_id",
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
        table_class_name="Location",
        tablename="location",
        column_name="name",
        db_column_name="name",
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
        table_class_name="Location",
        tablename="location",
        column_name="is_physical_location",
        db_column_name="is_physical_location",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": True,
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
        table_class_name="Location",
        tablename="location",
        column_name="address_line_1",
        db_column_name="address_line_1",
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
        table_class_name="Location",
        tablename="location",
        column_name="town_city",
        db_column_name="town_city",
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
        table_class_name="Location",
        tablename="location",
        column_name="county",
        db_column_name="county",
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
        table_class_name="Location",
        tablename="location",
        column_name="country",
        db_column_name="country",
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
        table_class_name="Location",
        tablename="location",
        column_name="postcode",
        db_column_name="postcode",
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
        table_class_name="Location",
        tablename="location",
        column_name="merchant_internal_id",
        db_column_name="merchant_internal_id",
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
        table_class_name="MIDVisaData",
        tablename="mid_visa_data",
        column_name="vsid",
        db_column_name="vsid",
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
        table_class_name="MIDVisaData",
        tablename="mid_visa_data",
        column_name="bin",
        db_column_name="bin",
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
        table_class_name="MIDVisaData",
        tablename="mid_visa_data",
        column_name="vmid",
        db_column_name="vmid",
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
        table_class_name="PaymentScheme",
        tablename="payment_scheme",
        column_name="slug",
        db_column_name="slug",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
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
        table_class_name="MIDMastercardData",
        tablename="mid_mastercard_data",
        column_name="location_id",
        db_column_name="location_id",
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
        table_class_name="Merchant",
        tablename="merchant",
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
        table_class_name="Merchant",
        tablename="merchant",
        column_name="name",
        db_column_name="name",
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
        table_class_name="Merchant",
        tablename="merchant",
        column_name="icon_url",
        db_column_name="icon_url",
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
        table_class_name="Merchant",
        tablename="merchant",
        column_name="slug",
        db_column_name="slug",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": None,
            "null": True,
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
        table_class_name="Merchant",
        tablename="merchant",
        column_name="plan_id",
        db_column_name="plan_id",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "default": None,
            "null": True,
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
        table_class_name="Merchant",
        tablename="merchant",
        column_name="location_label",
        db_column_name="location_label",
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
        table_class_name="MerchantToPaymentScheme",
        tablename="merchant_to_payment_scheme",
        column_name="merchant",
        db_column_name="merchant",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": Merchant,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
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
        table_class_name="MerchantToPaymentScheme",
        tablename="merchant_to_payment_scheme",
        column_name="payment_scheme",
        db_column_name="payment_scheme",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": PaymentScheme,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
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
