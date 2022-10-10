"""Merchant identifier table definitions."""
from piccolo.columns import ForeignKey, Text, Timestamptz

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.tables import TableWithPK


class Identifier(TableWithPK):
    """Represents a payment scheme's internal merchant identifier (PSIMI)."""

    value = Text(required=True, unique=True)
    payment_scheme = ForeignKey(PaymentScheme, required=True)
    payment_scheme_merchant_name = Text(required=True)
    date_added = Timestamptz()
    txm_status = Text(choices=TXMStatus, default=TXMStatus.NOT_ONBOARDED)
    status = Text(choices=ResourceStatus, default=ResourceStatus.ACTIVE)
    merchant = ForeignKey(Merchant, required=True)
