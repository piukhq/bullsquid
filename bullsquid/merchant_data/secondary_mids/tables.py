"""Secondary MID table definitions."""

from piccolo.columns import M2M, ForeignKey, LazyTableReference, Text, Timestamptz

from bullsquid.merchant_data.enums import PaymentEnrolmentStatus, TXMStatus
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.tables import BaseTable


class SecondaryMID(BaseTable):
    """Represents a secondary MID value."""

    secondary_mid = Text(required=True)
    payment_scheme = ForeignKey(PaymentScheme, required=True)
    payment_scheme_store_name = Text(null=True, default=None)
    date_added = Timestamptz()
    payment_enrolment_status = Text(
        choices=PaymentEnrolmentStatus, default=PaymentEnrolmentStatus.UNKNOWN
    )
    txm_status = Text(choices=TXMStatus, default=TXMStatus.NOT_ONBOARDED)
    merchant = ForeignKey(Merchant, required=True)

    locations = M2M(LazyTableReference("SecondaryMIDLocationLink", "merchant_data"))

    @property
    def display_text(self) -> str:
        return self.secondary_mid
