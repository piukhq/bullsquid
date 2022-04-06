"""Ensures tests are run through the Piccolo test runner."""
import contextlib
import os
import sys
from typing import Any, Dict, Generator, Mapping, Protocol, Type, TypeVar, cast

import pytest
from asyncpg import DuplicateTableError
from fastapi.testclient import TestClient
from piccolo.columns import Column
from piccolo.conf.apps import Finder
from piccolo.table import Table, create_tables, drop_tables
from piccolo.testing.model_builder import ModelBuilder
from piccolo.utils.warnings import colored_warning
from pydantic import BaseModel

from bullsquid.api.app import create_app


def pytest_configure() -> None:
    """Ensures tests are run through the Piccolo test runner."""
    if os.environ.get("PICCOLO_TEST_RUNNER") != "True":
        colored_warning(
            "\n\n"
            "We recommend running Piccolo tests using the "
            "`piccolo tester run` command, which wraps Pytest, and makes "
            "sure the test database is being used. "
            "To stop this warning, modify conftest.py."
            "\n\n"
        )
        sys.exit(1)


@pytest.fixture(autouse=True)
def all_tables() -> Generator[None, None, None]:
    """Creates all required tables for the duration of the test session."""
    tables = Finder().get_table_classes()
    try:
        create_tables(*tables)
    except DuplicateTableError:
        colored_warning(
            "\n\n"
            "The test database already contains tables. "
            "This could be due to a previous test run that did not exit cleanly. "
            "Please ensure that the test database is empty, "
            "and the tests are not connecting to a non-test database."
            "\n\n"
        )
        raise
    yield
    drop_tables(*tables)


TModel_co = TypeVar("TModel_co", bound=Table, covariant=True)


class ModelFactory(Protocol[TModel_co]):
    """A protocol for factory that creates a model instance."""

    def get(self, *, persist: bool = True, **defaults: Any) -> TModel_co:
        """Create and return a model instance."""


ModelFactoryFixture = Generator[Type[ModelFactory], None, None]


class ModelFactoryMaker(Protocol):
    """Callback protocol for the type that model_factory returns."""

    def __call__(
        self, table: Type[TModel_co], **baked_defaults: Any
    ) -> ModelFactoryFixture:
        ...


@pytest.fixture
def model_factory() -> ModelFactoryMaker:
    """Returns a function that creates a model factory for a given table."""

    def factory(table: Type[TModel_co], **baked_defaults: Any) -> ModelFactoryFixture:
        """Returns a factory class for the given table."""
        with contextlib.ExitStack() as stack:

            def get(*, persist: bool = True, **defaults: Any) -> TModel_co:
                """
                Builds a randomised model in the database and returns it.
                The model is automatically deleted after the test.
                """
                full_defaults = baked_defaults.copy()
                full_defaults.update(defaults)
                obj = ModelBuilder.build_sync(
                    table_class=table,
                    defaults=cast(Dict[Column | str, Any], full_defaults),
                    persist=persist,
                )
                stack.callback(lambda: obj.remove().run_sync())
                return cast(TModel_co, obj)

            yield type(f"{table.__name__}ModelFactory", (ModelFactory,), {"get": get})

    return factory


@pytest.fixture
def test_client() -> TestClient:
    """Creates a FastAPI test client for the app."""
    app = create_app()
    return TestClient(app)


def ser(table: Table, model: BaseModel) -> Mapping[str, Any]:
    """Serialise a piccolo object to a dict using the given model."""
    return model.parse_obj(table.to_dict()).dict()
