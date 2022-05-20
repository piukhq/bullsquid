"""Database access layer for operating on payment schemes."""

from .tables import PaymentScheme


async def list_payment_schemes() -> list[PaymentScheme]:
    """Return a list of all payment schemes."""
    return await PaymentScheme.objects()


async def get_payment_scheme_by_code(code: int) -> PaymentScheme:
    """Return the payment scheme with the given code."""
    return await PaymentScheme.objects().where(PaymentScheme.code == code).first()
