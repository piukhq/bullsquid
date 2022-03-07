"""Definitions of all the table models used for MID management."""
from enum import Enum

from piccolo.columns import UUID, Boolean, ForeignKey, Integer, Text
from piccolo.columns.m2m import M2M
from piccolo.columns.reference import LazyTableReference
from piccolo.table import Table


class Merchant(Table):
    """Represents a merchant such as Iceland or Wasabi."""

    pk = UUID(primary_key=True)
    name = Text(required=True, unique=True)
    icon_url = Text(null=True, default=None)
    slug = Text(null=True, default=None, unique=True)
    payment_schemes = M2M(LazyTableReference("MerchantToPaymentScheme", "mids"))
    plan_id = Integer(null=True, default=None, unique=True)
    location_label = Text(required=True)


class PaymentScheme(Table):
    """Represents a payment scheme such as Visa or Amex."""

    slug = Text(primary_key=True)
    merchants = M2M(LazyTableReference("MerchantToPaymentScheme", "mids"))


class MerchantToPaymentScheme(Table):
    """Links a merchant to the payment schemes it is interested in."""

    merchant = ForeignKey(Merchant, null=False)
    payment_scheme = ForeignKey(PaymentScheme, null=False)


class Location(Table):
    """Represents a location that can have multiple MIDs."""

    pk = UUID(primary_key=True)
    location_id = Text(required=True, unique=True)
    name = Text(required=True)
    is_physical_location = Boolean(default=True)
    address_line_1 = Text(null=True, default=None)
    town_city = Text(null=True, default=None)
    county = Text(null=True, default=None)
    country = Text(null=True, default=None)
    postcode = Text(null=True, default=None)
    merchant_internal_id = Text(null=True, default=None)


class MIDMastercardData(Table):
    """Extra data attached to mastercard MIDs."""

    location_id = Text(null=True, default=None)


class MIDVisaData(Table):
    """Extra data attached to visa MIDs."""

    vsid = Text(null=True, default=None)
    bin = Text(null=True, default=None)
    vmid = Text(null=True, default=None)


class MID(Table):
    """Represents a merchant identifier."""

    class PaymentEnrolmentStatus(Enum):
        """Current status of the MID with payment schemes."""

        UNKNOWN = "unknown"
        ENROLLING = "enrolling"
        ENROLLED = "enrolled"
        FAILED = "failed"

    class TXMStatus(Enum):
        """Current status of the MID in transaction matching."""

        NOT_ONBOARDED = "not_onboarded"
        ONBOARDED = "onboarded"
        OFFBOARDED = "offboarded"

    pk = UUID(primary_key=True)
    mid = Text(null=True, default=None, unique=True)
    payment_scheme = ForeignKey(PaymentScheme, required=True, null=False)
    payment_enrolment_status = Text(
        choices=PaymentEnrolmentStatus, default=PaymentEnrolmentStatus.UNKNOWN
    )
    txm_status = Text(choices=TXMStatus, default=TXMStatus.NOT_ONBOARDED)
    mastercard_data = ForeignKey(
        MIDMastercardData, null=True, default=None, unique=True
    )
    visa_data = ForeignKey(MIDVisaData, null=True, default=None, unique=True)
