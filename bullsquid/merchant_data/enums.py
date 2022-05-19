"""Common place for enumerations used in the API and database."""
from enum import Enum


class PlanStatus(str, Enum):
    """Status enum used for plans and merchants."""

    ACTIVE = "active"  # live, available for use
    DRAFT = "draft"  # actively being set up
    COMING_SOON = "coming_soon"  # awaiting publishing
    SUSPENDED = "suspended"  # temporarily hidden
    PENDING_DELETION = "pending_deletion"  # delete in progress
    DELETED = "deleted"  # soft deleted


class PaymentEnrolmentStatus(str, Enum):
    """Current status of a MID with payment schemes."""

    UNKNOWN = "unknown"
    ENROLLING = "enrolling"
    ENROLLED = "enrolled"
    REMOVED = "removed"


class TXMStatus(str, Enum):
    """Current status of a MID in transaction matching."""

    NOT_ONBOARDED = "not_onboarded"
    ONBOARDED = "onboarded"
    OFFBOARDED = "offboarded"
