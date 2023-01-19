"""Test for the top level database module."""
from typing import Any, AsyncGenerator, Type

import pytest
from piccolo.columns import Text
from piccolo.table import Table, create_db_tables, drop_db_tables

from bullsquid.db import paginate


@pytest.fixture
async def test_table() -> AsyncGenerator[Type[Table], None]:
    """Creates TestTable and inserts some records."""

    class TestTable(Table):
        """Test table model."""

        name = Text()

    await create_db_tables(TestTable)
    await TestTable.insert(
        TestTable(name="test-1"),
        TestTable(name="test-2"),
        TestTable(name="test-3"),
        TestTable(name="test-4"),
        TestTable(name="test-5"),
    )
    yield TestTable
    await drop_db_tables(TestTable)


def names(results: list[dict[str, Any]]) -> list[str]:
    """Returns a list of names from the given results."""
    return [result["name"] for result in results]


async def test_correct_pagination(test_table: Table) -> None:
    query = test_table.select()

    results = await paginate(query, n=2, p=1)
    assert names(results) == ["test-1", "test-2"]

    results = await paginate(query, n=3, p=1)
    assert names(results) == ["test-1", "test-2", "test-3"]

    results = await paginate(query, n=3, p=2)
    assert names(results) == ["test-4", "test-5"]


async def test_paginate_n_zero(test_table: Table) -> None:
    query = test_table.select()

    with pytest.raises(ValueError) as ex:
        await paginate(query, n=0, p=1)

    assert str(ex.value) == "n must be >= 1"


async def test_paginate_n_negative(test_table: Table) -> None:
    query = test_table.select()

    with pytest.raises(ValueError) as ex:
        await paginate(query, n=-3, p=1)

    assert str(ex.value) == "n must be >= 1"


async def test_paginate_p_zero(test_table: Table) -> None:
    query = test_table.select()

    with pytest.raises(ValueError) as ex:
        await paginate(query, n=5, p=0)

    assert str(ex.value) == "p must be >= 1"


async def test_paginate_p_negative(test_table: Table) -> None:
    query = test_table.select()

    with pytest.raises(ValueError) as ex:
        await paginate(query, n=5, p=-3)

    assert str(ex.value) == "p must be >= 1"
