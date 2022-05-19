"""Database access layer for operating on payment schemes."""

from .tables import PaymentScheme


async def list_payment_schemes() -> list[PaymentScheme]:
    """Return a list of all payment schemes."""
    return await PaymentScheme.objects()
