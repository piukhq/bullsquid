"""Common place for enumerations used in the API and database."""

from enum import Enum


class ResourceType(str, Enum):
    """
    An enum representing the types of resources that can be managed in the
    merchant data portal.
    """

    PLAN = "plan"
    MERCHANT = "merchant"
    LOCATION = "location"
    PRIMARY_MID = "mid"
    SECONDARY_MID = "secondary_mid"
    PSIMI = "psimi"


class FilterSubjectType(Enum):
    """
    All the ResourceTypes except plan.
    Used as a parameter to filter comments by subject type.
    """

    MERCHANT = ResourceType.MERCHANT.value
    LOCATION = ResourceType.LOCATION.value
    PRIMARY_MID = ResourceType.PRIMARY_MID.value
    SECONDARY_MID = ResourceType.SECONDARY_MID.value
    PSIMI = ResourceType.PSIMI.value


class ResourceStatus(str, Enum):
    """Status enum shared between most publishable/deletable resources."""

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
    FAILED = "failed"
    NOT_ENROLLED = "not_enrolled"
    REMOVED = "removed"


class TXMStatus(str, Enum):
    """Current status of a MID in transaction matching."""

    NOT_ONBOARDED = "not_onboarded"
    ONBOARDED = "onboarded"
    OFFBOARDED = "offboarded"
