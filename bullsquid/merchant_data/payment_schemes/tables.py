"""Payment scheme table definitions."""

from piccolo.columns import Text
from piccolo.table import Table


class PaymentScheme(Table):
    """Represents a payment scheme such as Visa or Amex."""

    slug = Text(primary_key=True)
