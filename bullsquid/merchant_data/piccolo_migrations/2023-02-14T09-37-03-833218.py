from enum import Enum

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text

ID = "2023-02-14T09:37:03:833218"
VERSION = "0.97.0"
DESCRIPTION = "add missing enrolment statuses"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="PrimaryMID",
        tablename="primary_mid",
        column_name="payment_enrolment_status",
        db_column_name="payment_enrolment_status",
        params={
            "choices": Enum(
                "PaymentEnrolmentStatus",
                {
                    "UNKNOWN": "unknown",
                    "ENROLLING": "enrolling",
                    "ENROLLED": "enrolled",
                    "FAILED": "failed",
                    "NOT_ENROLLED": "not_enrolled",
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
                    "REMOVED": "removed",
                },
            )
        },
        column_class=Text,
        old_column_class=Text,
    )

    manager.alter_column(
        table_class_name="SecondaryMID",
        tablename="secondary_mid",
        column_name="payment_enrolment_status",
        db_column_name="payment_enrolment_status",
        params={
            "choices": Enum(
                "PaymentEnrolmentStatus",
                {
                    "UNKNOWN": "unknown",
                    "ENROLLING": "enrolling",
                    "ENROLLED": "enrolled",
                    "FAILED": "failed",
                    "NOT_ENROLLED": "not_enrolled",
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
                    "REMOVED": "removed",
                },
            )
        },
        column_class=Text,
        old_column_class=Text,
    )

    return manager
