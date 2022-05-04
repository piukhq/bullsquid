"""Definitions of all the table models used for MID management."""
from enum import Enum

from piccolo.columns import UUID, Boolean, ForeignKey, Integer, Text, Timestamptz
from piccolo.table import Table


class PlanStatus(Enum):
    """Status enum used for plans and merchants."""

    ACTIVE = "active"  # live, available for use
    DRAFT = "draft"  # actively being set up
    COMING_SOON = "coming_soon"  # awaiting publishing
    SUSPENDED = "suspended"  # temporarily hidden
    PENDING_DELETION = "pending_deletion"  # delete in progress
    DELETED = "deleted"  # soft deleted


class Plan(Table):
    """Represents a loyalty plan that may contain any number of merchants."""

    pk = UUID(primary_key=True)
    name = Text(required=True, unique=True)
    status = Text(choices=PlanStatus, default=PlanStatus.ACTIVE)
    icon_url = Text(null=True, default=None)
    slug = Text(null=True, default=None, unique=True)
    plan_id = Integer(null=True, default=None, unique=True)
    is_deleted = Boolean(default=False)


class Merchant(Table):
    """Represents a merchant such as Iceland or Wasabi."""

    pk = UUID(primary_key=True)
    name = Text(required=True, unique=True)
    status = Text(choices=PlanStatus, default=PlanStatus.ACTIVE)
    icon_url = Text(null=True, default=None)
    location_label = Text(required=True)
    is_deleted = Boolean(default=False)
    plan = ForeignKey(Plan, required=True, null=False)


class PaymentScheme(Table):
    """Represents a payment scheme such as Visa or Amex."""

    slug = Text(primary_key=True)


class Location(Table):
    """Represents a location that can have multiple MIDs."""

    pk = UUID(primary_key=True)
    location_id = Text(required=True)
    name = Text(required=True)
    is_physical_location = Boolean(default=True)
    address_line_1 = Text(null=True, default=None)
    address_line_2 = Text(null=True, default=None)
    town_city = Text(null=True, default=None)
    county = Text(null=True, default=None)
    country = Text(null=True, default=None)
    postcode = Text(null=True, default=None)
    merchant_internal_id = Text(null=True, default=None)
    merchant = ForeignKey(Merchant, required=True, null=False)


class PrimaryMID(Table):
    """Represents a merchant identifier."""

    class PaymentEnrolmentStatus(Enum):
        """Current status of the MID with payment schemes."""

        UNKNOWN = "unknown"
        ENROLLING = "enrolling"
        ENROLLED = "enrolled"
        REMOVED = "removed"

    class TXMStatus(Enum):
        """Current status of the MID in transaction matching."""

        NOT_ONBOARDED = "not_onboarded"
        ONBOARDED = "onboarded"
        OFFBOARDED = "offboarded"

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


class MerchantIdentifier(Table):
    """Represents a payment scheme's internal merchant identifier."""

    pk = UUID(primary_key=True)
    value = Text(required=True, unique=True)
    payment_scheme = ForeignKey(PaymentScheme, required=True)
    name = Text(required=True)
    date_added = Timestamptz()
    is_deleted = Boolean(default=False)
    merchant = ForeignKey(Merchant, required=True, null=False)
