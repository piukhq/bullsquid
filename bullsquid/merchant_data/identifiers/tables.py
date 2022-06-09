"""Merchant identifier table definitions."""
from piccolo.columns import UUID, ForeignKey, Text, Timestamptz
from piccolo.table import Table

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme


class Identifier(Table):
    """Represents a payment scheme's internal merchant identifier (PSIMI)."""

    pk = UUID(primary_key=True)
    value = Text(required=True, unique=True)
    payment_scheme = ForeignKey(PaymentScheme, required=True)
    name = Text(required=True)
    date_added = Timestamptz()
    txm_status = Text(choices=TXMStatus, default=TXMStatus.NOT_ONBOARDED)
    status = Text(choices=ResourceStatus, default=ResourceStatus.ACTIVE)
    merchant = ForeignKey(Merchant, required=True)
