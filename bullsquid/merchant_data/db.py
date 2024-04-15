"""
Top-level database utilities for the whole merchant data module.
"""

from typing import Type

from bullsquid.merchant_data.enums import ResourceType
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.psimis.tables import PSIMI
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from bullsquid.merchant_data.tables import BaseTable

RESOURCE_TYPE_TO_TABLE: dict[ResourceType, Type[BaseTable]] = {
    ResourceType.PLAN: Plan,
    ResourceType.MERCHANT: Merchant,
    ResourceType.LOCATION: Location,
    ResourceType.PRIMARY_MID: PrimaryMID,
    ResourceType.SECONDARY_MID: SecondaryMID,
    ResourceType.PSIMI: PSIMI,
}

assert all(resource_type in RESOURCE_TYPE_TO_TABLE for resource_type in ResourceType)
