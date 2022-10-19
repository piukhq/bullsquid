"""Primary MID table definitions."""
from piccolo.columns import ForeignKey, Text, Timestamptz

from bullsquid.merchant_data.enums import (
    PaymentEnrolmentStatus,
    ResourceStatus,
    TXMStatus,
)
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.tables import TableWithPK


class PrimaryMID(TableWithPK):
    """Represents a primary MID value."""

    mid = Text(unique=True)
    visa_bin = Text(null=True, default=None)
    payment_scheme = ForeignKey(PaymentScheme, required=True)
    date_added = Timestamptz()
    payment_enrolment_status = Text(
        choices=PaymentEnrolmentStatus, default=PaymentEnrolmentStatus.UNKNOWN
    )
    txm_status = Text(choices=TXMStatus, default=TXMStatus.NOT_ONBOARDED)
    status = Text(choices=ResourceStatus, default=ResourceStatus.ACTIVE, index=True)
    merchant = ForeignKey(Merchant, required=True)
    location = ForeignKey(Location)

    @property
    def display_text(self) -> str:
        return self.mid
