"""Primary MID table definitions."""
from piccolo.columns import UUID, Boolean, ForeignKey, Text, Timestamptz
from piccolo.table import Table

from bullsquid.merchant_data.enums import PaymentEnrolmentStatus, TXMStatus
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme


class PrimaryMID(Table):
    """Represents a merchant identifier."""

    pk = UUID(primary_key=True)
    mid = Text(unique=True)
    visa_bin = Text(null=True, default=None)
    payment_scheme = ForeignKey(PaymentScheme, required=True, null=False)
    date_added = Timestamptz()
    payment_enrolment_status = Text(
        choices=PaymentEnrolmentStatus, default=PaymentEnrolmentStatus.UNKNOWN
    )
    txm_status = Text(choices=TXMStatus, default=TXMStatus.NOT_ONBOARDED)
    is_deleted = Boolean(default=False)
    merchant = ForeignKey(Merchant, required=True, null=False)
    location = ForeignKey(Location, null=True, default=None)
