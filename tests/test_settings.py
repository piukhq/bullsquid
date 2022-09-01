"""Tests for settings validation."""

import os
from unittest.mock import patch

from ward import raises, test

from bullsquid.settings import Settings

TXM_SETTING_MSG = """
1 validation error for TXMSettings
__root__
  If one TXM setting is provided, all others must also be provided. (type=value_error)
""".strip()


@test("TXM base URL is required if TXM API key is set")
def _() -> None:
    with patch.dict(os.environ, {"txm_api_key": "foo"}):
        with raises(ValueError) as ex:
            Settings()

        assert str(ex.raised) == TXM_SETTING_MSG


@test("TXM API key is required if TXM base url is set")
def _() -> None:
    with patch.dict(os.environ, {"txm_base_url": "https://testbink.com"}):
        with raises(ValueError) as ex:
            Settings()

        assert str(ex.raised) == TXM_SETTING_MSG
