"""Harmonia service class."""
from unittest.mock import MagicMock, create_autospec
from uuid import UUID

from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.service import ServiceInterface
from bullsquid.settings import settings


class TXMServiceInterface(ServiceInterface):
    """Interface into the transaction matching API."""

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url)
        self.headers = {"Authorization": f"Token {settings.txm.api_key}"}

    async def onboard_mids(self, mid_refs: list[UUID]) -> dict:
        """Onboard MIDs into Harmonia."""
        identifiers = await PrimaryMID.select(
            PrimaryMID.mid.as_alias("identifier"),
            PrimaryMID.merchant.plan.slug.as_alias("loyalty_plan"),  # type: ignore
            PrimaryMID.payment_scheme.slug.as_alias("payment_scheme"),
            PrimaryMID.location.location_id.as_alias("location_id"),
        ).where(PrimaryMID.pk.is_in(mid_refs))
        for identifier in identifiers:
            identifier["identifier_type"] = "PRIMARY"

        return await self.post("/txm/identifiers/", {"identifiers": identifiers})

    async def offboard_mids(self, mid_refs: list[UUID]) -> dict:
        """Offboard MIDs from Harmonia."""
        identifiers = await PrimaryMID.select(
            PrimaryMID.mid,
            PrimaryMID.payment_scheme.slug.as_alias("payment_scheme"),
        ).where(PrimaryMID.pk.is_in(mid_refs))

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
