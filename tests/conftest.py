import os

from piccolo.table import create_db_tables_sync, drop_db_tables_sync

os.environ["PICCOLO_CONF"] = "piccolo_conf_test"
os.environ["debug"] = "true"
os.environ.pop("txm_base_url", None)
os.environ.pop("txm_api_key", None)

from typing import Generator

import pytest
from aioresponses import aioresponses
from asyncpg import DuplicateTableError
from fastapi.testclient import TestClient
from piccolo.conf.apps import Finder
from piccolo.utils.warnings import colored_warning

from bullsquid.api.app import create_app


@pytest.fixture()
def database() -> Generator[None, None, None]:
    """
    Creates all database tables at the start of the test session.
    In theory, this can run in global scope. To do so, the model factories need
    to clean up after each test themselves. This is non-trivial.
    """
    tables = Finder().get_table_classes()
    try:
        create_db_tables_sync(*tables)
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
    drop_db_tables_sync(*tables)


@pytest.fixture
def test_client() -> TestClient:
    """Creates a FastAPI test client for the app."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_responses() -> Generator[aioresponses, None, None]:
    """
    Mock responses for all external API requests.
    """
    with aioresponses() as mock:
        yield mock
