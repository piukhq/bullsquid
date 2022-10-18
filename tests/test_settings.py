"""Tests for settings validation."""

import os
from unittest.mock import patch

import pytest

from bullsquid.settings import Settings

TXM_SETTING_MSG = """
1 validation error for TXMSettings
__root__
  If one TXM setting is provided, all others must also be provided. (type=value_error)
""".strip()


def test_txm_base_url_is_required() -> None:
    with patch.dict(os.environ, {"txm_api_key": "foo"}):
        with pytest.raises(ValueError) as ex:
            Settings()

        assert str(ex.value) == TXM_SETTING_MSG


def test_txm_api_key_is_required() -> None:
    with patch.dict(os.environ, {"txm_base_url": "https://testbink.com"}):
        with pytest.raises(ValueError) as ex:
            Settings()

        assert str(ex.value) == TXM_SETTING_MSG
