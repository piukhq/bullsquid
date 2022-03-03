"""Definitions of all the table models used for MID management."""
from piccolo.columns import UUID, ForeignKey, Integer, Text
from piccolo.columns.m2m import M2M
from piccolo.columns.reference import LazyTableReference
from piccolo.table import Table


class Merchant(Table):
    """Represents a merchant such as Iceland or Wasabi."""

    pk = UUID(primary_key=True)
    name = Text(required=True, unique=True)
    icon_url = Text(null=True)
    slug = Text(null=True, unique=True)
    payment_schemes = M2M(LazyTableReference("MerchantToPaymentScheme", "mids"))
    plan_id = Integer(null=True, unique=True)
    location_label = Text(required=True)


class PaymentScheme(Table):
    """Represents a payment scheme such as Visa or Amex."""

    slug = Text(primary_key=True)
    merchants = M2M(LazyTableReference("MerchantToPaymentScheme", "mids"))


class MerchantToPaymentScheme(Table):
    """Links a merchant to the payment schemes it is interested in."""

    merchant = ForeignKey(Merchant)
    payment_scheme = ForeignKey(PaymentScheme)
