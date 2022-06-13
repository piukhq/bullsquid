"""Test for the top level database module."""
from typing import Any, AsyncGenerator

from piccolo.columns import Text
from piccolo.table import Table, create_tables, drop_tables
from ward import fixture, raises, test

from bullsquid.db import paginate


class TestTable(Table):
    """Test table model."""

    name = Text()


@fixture
async def test_table() -> AsyncGenerator[None, None]:
    """Creates TestTable and inserts some records."""
    create_tables(TestTable)
    await TestTable.insert(
        TestTable(name="test-1"),
        TestTable(name="test-2"),
        TestTable(name="test-3"),
        TestTable(name="test-4"),
        TestTable(name="test-5"),
    )
    yield
    drop_tables(TestTable)


def names(results: list[dict[str, Any]]) -> list[str]:
    """Returns a list of names from the given results."""
    return [result["name"] for result in results]


@test("paginate correctly paginates a simple query")
async def _(_db: None = test_table) -> None:
    query = TestTable.select()

    results = await paginate(query, n=2, p=1)
    assert names(results) == ["test-1", "test-2"]

    results = await paginate(query, n=3, p=1)
    assert names(results) == ["test-1", "test-2", "test-3"]

    results = await paginate(query, n=3, p=2)
    assert names(results) == ["test-4", "test-5"]


@test("paginate raises an error if n is zero")
async def _(_db: None = test_table) -> None:
    query = TestTable.select()

    with raises(ValueError) as ex:
        await paginate(query, n=0, p=1)

    assert str(ex.raised) == "n must be >= 1"


@test("paginate raises an error if n is negative")
async def _(_db: None = test_table) -> None:
    query = TestTable.select()

    with raises(ValueError) as ex:
        await paginate(query, n=-3, p=1)

    assert str(ex.raised) == "n must be >= 1"


@test("paginate raises an error if p is zero")
async def _(_db: None = test_table) -> None:
    query = TestTable.select()

    with raises(ValueError) as ex:
        await paginate(query, n=5, p=0)

    assert str(ex.raised) == "p must be >= 1"


@test("paginate raises an error if p is negative")
async def _(_db: None = test_table) -> None:
    query = TestTable.select()

    with raises(ValueError) as ex:
        await paginate(query, n=5, p=-3)

    assert str(ex.raised) == "p must be >= 1"
