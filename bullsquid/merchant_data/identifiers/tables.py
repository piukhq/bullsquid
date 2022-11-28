"""Merchant identifier table definitions."""
from piccolo.columns import ForeignKey, Text, Timestamptz

from bullsquid.merchant_data.enums import TXMStatus
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.tables import BaseTable


class Identifier(BaseTable):
    """Represents a payment scheme's internal merchant identifier (PSIMI)."""

    value = Text(required=True, unique=True)
    payment_scheme = ForeignKey(PaymentScheme, required=True)
    payment_scheme_merchant_name = Text(required=True)
    date_added = Timestamptz()
    txm_status = Text(choices=TXMStatus, default=TXMStatus.NOT_ONBOARDED)
    merchant = ForeignKey(Merchant, required=True)

    @property
    def display_text(self) -> str:
        return self.value
