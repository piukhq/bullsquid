"""Harmonia service class."""
from unittest.mock import MagicMock, create_autospec
from uuid import UUID

from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.psimis.tables import PSIMI
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from bullsquid.service import ServiceInterface
from bullsquid.settings import settings


class TXMServiceInterface(ServiceInterface):
    """Interface into the transaction matching API."""

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url)
        self.headers = {"Authorization": f"Token {settings.txm.api_key}"}

    async def onboard_mids(self, mid_refs: set[UUID]) -> dict:
        """Onboard MIDs into Harmonia."""
        identifiers = await PrimaryMID.select(
            PrimaryMID.mid.as_alias("identifier"),
            PrimaryMID.merchant.plan.slug.as_alias("loyalty_plan"),  # type: ignore
            PrimaryMID.payment_scheme.slug.as_alias("payment_scheme"),
            PrimaryMID.location.location_id.as_alias("location_id"),
        ).where(PrimaryMID.pk.is_in(list(mid_refs)))
        for identifier in identifiers:
            identifier["identifier_type"] = "PRIMARY"

        return await self.post("/txm/identifiers/", {"identifiers": identifiers})

    async def onboard_secondary_mids(self, secondary_mid_refs: set[UUID]) -> dict:
        """Onboard Secondary MIDs into Harmonia."""
        identifiers = await SecondaryMID.select(
            SecondaryMID.secondary_mid.as_alias("identifier"),
            SecondaryMID.merchant.plan.slug.as_alias("loyalty_plan"),  # type: ignore
            SecondaryMID.payment_scheme.slug.as_alias("payment_scheme"),
        ).where(SecondaryMID.pk.is_in(list(secondary_mid_refs)))
        for identifier in identifiers:
            identifier["identifier_type"] = "SECONDARY"

        return await self.post("/txm/identifiers/", {"identifiers": identifiers})

    async def onboard_psimis(self, psimi_refs: set[UUID]) -> dict:
        """Onboard PSIMIs into Harmonia."""
        identifiers = await PSIMI.select(
            PSIMI.value.as_alias("identifier"),
            PSIMI.merchant.plan.slug.as_alias("loyalty_plan"),  # type: ignore
            PSIMI.payment_scheme.slug.as_alias("payment_scheme"),
        ).where(PSIMI.pk.is_in(list(psimi_refs)))
        for identifier in identifiers:
            identifier["identifier_type"] = "PSIMI"

        return await self.post("/txm/identifiers/", {"identifiers": identifiers})

    async def offboard_mids(self, mid_refs: set[UUID]) -> dict:
        """Offboard MIDs from Harmonia."""
        identifiers = await PrimaryMID.select(
            PrimaryMID.mid.as_alias("identifier"),
            PrimaryMID.payment_scheme.slug.as_alias("payment_scheme"),
        ).where(PrimaryMID.pk.is_in(list(mid_refs)))
        for identifier in identifiers:
            identifier["identifier_type"] = "PRIMARY"

        return await self.post(
            "/txm/identifiers/deletion", {"identifiers": identifiers, "locations": []}
        )

    async def offboard_secondary_mids(self, secondary_mid_refs: set[UUID]) -> dict:
        """Offboard Secondary MIDs from Harmonia."""
        identifiers = await SecondaryMID.select(
            SecondaryMID.secondary_mid.as_alias("identifier"),
            SecondaryMID.payment_scheme.slug.as_alias("payment_scheme"),
        ).where(SecondaryMID.pk.is_in(list(secondary_mid_refs)))
        for identifier in identifiers:
            identifier["identifier_type"] = "SECONDARY"

        return await self.post(
            "/txm/identifiers/deletion", {"identifiers": identifiers, "locations": []}
        )

    async def offboard_psimis(self, psimi_refs: set[UUID]) -> dict:
        """Offboard PSIMIs from Harmonia."""
        identifiers = await PSIMI.select(
            PSIMI.value.as_alias("identifier"),
            PSIMI.payment_scheme.slug.as_alias("payment_scheme"),
        ).where(PSIMI.pk.is_in(list(psimi_refs)))
        for identifier in identifiers:
            identifier["identifier_type"] = "PSIMI"

        return await self.post(
            "/txm/identifiers/deletion", {"identifiers": identifiers, "locations": []}
        )


def create_txm_service_interface() -> TXMServiceInterface | MagicMock:
    """Return a TXM service interface, mocked if no base URL is set."""
    return (
        TXMServiceInterface(settings.txm.base_url)
        if settings.txm.base_url
        else create_autospec(TXMServiceInterface)
    )


txm = create_txm_service_interface()
