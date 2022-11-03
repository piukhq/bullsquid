"""Database access layer for operating on payment schemes."""

from bullsquid.db import NoSuchRecord

from .tables import PaymentScheme


async def list_payment_schemes() -> list[PaymentScheme]:
    """Return a list of all payment schemes."""
    return await PaymentScheme.objects()


async def get_payment_scheme(slug: str) -> PaymentScheme:
    """Get a payment scheme object by its slug."""
    payment_scheme = await PaymentScheme.objects().get(PaymentScheme.slug == slug)
    if not payment_scheme:
        raise NoSuchRecord(PaymentScheme)
    return payment_scheme
