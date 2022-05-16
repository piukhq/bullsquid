"""Ward fixture functions."""
from typing import Generator, TypeVar

from asyncpg import DuplicateTableError
from fastapi.testclient import TestClient
from piccolo.conf.apps import Finder
from piccolo.table import Table, create_tables, drop_tables
from piccolo.utils.warnings import colored_warning
from ward import Scope, fixture

from bullsquid.api.app import create_app
from settings import settings


@fixture(scope=Scope.Global)
def auth_header() -> dict:
    """Fills out the Authorization header with the configured API key."""
    return {
        "Authorization": f"token {settings.api_key}",
    }


@fixture()
def database() -> Generator[None, None, None]:
    """
    Creates all database tables at the start of the test session.
    In theory, this can run in global scope. To do so, the model factories need
    to clean up after each test themselves. This is non-trivial.
    """
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


@fixture
def test_client() -> TestClient:
    """Creates a FastAPI test client for the app."""
    app = create_app()
    return TestClient(app)
