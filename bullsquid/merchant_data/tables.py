"""
Base merchant data tables.
"""
from piccolo.columns import UUID
from piccolo.table import Table


class TableWithPK(Table):
    """
    Base table with a UUID primary key.
    """

    pk = UUID(primary_key=True)

    @property
    def display_text(self) -> str:
        """
        The pretty printable text for this table.
        """
        raise NotImplementedError
