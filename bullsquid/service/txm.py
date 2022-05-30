"""Harmonia service class."""
from unittest.mock import MagicMock, create_autospec
from uuid import UUID

from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.service import ServiceInterface
from settings import settings


class TXMServiceInterface(ServiceInterface):
    """Interface into the transaction matching API."""

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url)
        self.headers = {"Authorization": f"Token {settings.txm.api_key}"}

    async def onboard_mids(self, mid_refs: list[UUID]) -> dict:
        """Onboard MIDs into Harmonia."""
        mids = await PrimaryMID.select(
            PrimaryMID.mid,
            PrimaryMID.merchant.plan.slug.as_alias("loyalty_plan"),
            PrimaryMID.payment_scheme.slug.as_alias("payment_scheme"),
            PrimaryMID.location.location_id.as_alias("location_id"),
        ).where(PrimaryMID.pk.is_in(mid_refs))

        return await self.post("/txm/mids/", {"mids": mids})

    async def offboard_mids(self, mid_refs: list[UUID]) -> dict:
        """Offboard MIDs from Harmonia."""
        mids = await PrimaryMID.select(
            PrimaryMID.mid,
            PrimaryMID.merchant.plan.slug.as_alias("loyalty_plan"),
            PrimaryMID.payment_scheme.slug.as_alias("payment_scheme"),
            PrimaryMID.location.location_id.as_alias("location_id"),
        ).where(PrimaryMID.pk.is_in(mid_refs))

        return await self.post("/txm/mids/deletion", {"mids": mids})


def create_txm_service_interface() -> TXMServiceInterface | MagicMock:
    """Return a TXM service interface, mocked if no base URL is set."""
    if not settings.txm.base_url:
        return create_autospec(TXMServiceInterface)

    return TXMServiceInterface(settings.txm.base_url)


txm = create_txm_service_interface()
