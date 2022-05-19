"""Payment scheme table definitions."""
from piccolo.columns import Integer, Text
from piccolo.table import Table


class PaymentScheme(Table):
    """Represents a payment scheme such as Visa or Amex."""

    slug = Text(primary_key=True)
    code = Integer(required=True, unique=True)
    label = Text(required=True)
