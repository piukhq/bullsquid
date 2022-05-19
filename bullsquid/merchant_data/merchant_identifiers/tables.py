"""Merchant identifier table definitions."""
from piccolo.columns import UUID, Boolean, ForeignKey, Text, Timestamptz
from piccolo.table import Table

from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme


class MerchantIdentifier(Table):
    """Represents a payment scheme's internal merchant identifier."""

    pk = UUID(primary_key=True)
    value = Text(required=True, unique=True)
    payment_scheme = ForeignKey(PaymentScheme, required=True)
    name = Text(required=True)
    date_added = Timestamptz()
    is_deleted = Boolean(default=False)
    merchant = ForeignKey(Merchant, required=True, null=False)
