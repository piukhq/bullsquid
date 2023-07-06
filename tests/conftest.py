import os

os.environ["PICCOLO_CONF"] = "piccolo_conf_test"
os.environ["debug"] = "true"
os.environ.pop("txm_base_url", None)
os.environ.pop("txm_api_key", None)


from typing import Generator  # noqa: E402

import pytest  # noqa: E402
from aioresponses import aioresponses  # noqa: E402
from asyncpg import DuplicateTableError  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from piccolo.conf.apps import Finder  # noqa: E402
from piccolo.table import create_db_tables_sync, drop_db_tables_sync  # noqa: E402
from piccolo.utils.warnings import (  # noqa: E402
    colored_warning,
)

from bullsquid.api.app import create_app  # noqa: E402


pytest_plugins = [
    "tests.merchant_data.fixtures",
    "tests.customer_wallet.fixtures",
    "tests.user_data.fixtures",
]


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
            "This could be due to a previous test run that did not exit "
            " cleanly. "
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
